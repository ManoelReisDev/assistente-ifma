"""Avaliação reproduzível do RAG, separada dos testes automatizados."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unicodedata
from typing import Any

from langchain_core.embeddings import Embeddings

from academic_assistant import __version__
from academic_assistant.config import Settings
from academic_assistant.generation import (
    GenerationError,
    InvokableModel,
    create_chat_model,
    generate_answer,
)
from academic_assistant.indexing import (
    IndexingError,
    LoadedIndex,
    create_embeddings,
    load_active_index,
)
from academic_assistant.prompts import SYSTEM_PROMPT
from academic_assistant.retrieval import (
    ContextNotCoveredError,
    ContextRequiredError,
    RetrievedEvidence,
    RetrievalContext,
    RetrievalError,
    RetrievalResult,
    applicable_document_ids,
    retrieve_evidence,
)
from academic_assistant.validation import (
    AnswerResult,
    AnswerStatus,
    GenerationValidationError,
)


class EvaluationError(RuntimeError):
    """A avaliação não pode produzir um relatório confiável."""


class EvaluationBudgetExceeded(EvaluationError):
    """O limite configurado de chamadas externas foi atingido."""


@dataclass(slots=True)
class CallBudget:
    limit: int
    embedding_calls: int = 0
    generation_calls: int = 0

    @property
    def total(self) -> int:
        return self.embedding_calls + self.generation_calls

    def consume(self, kind: str) -> None:
        if self.total >= self.limit:
            raise EvaluationBudgetExceeded(
                f"Limite de {self.limit} chamadas externas atingido."
            )
        if kind == "embedding":
            self.embedding_calls += 1
        elif kind == "generation":
            self.generation_calls += 1
        else:
            raise EvaluationError(f"Tipo de chamada desconhecido: {kind}.")


class BudgetedModel:
    """Conta cada invoke real, inclusive a revisão limitada da geração."""

    def __init__(self, model: InvokableModel, budget: CallBudget) -> None:
        self.model = model
        self.budget = budget

    def bind(self, **kwargs: Any) -> "BudgetedModel":
        return BudgetedModel(self.model.bind(**kwargs), self.budget)

    def invoke(self, input: Any, **kwargs: Any) -> Any:
        self.budget.consume("generation")
        return self.model.invoke(input, **kwargs)


def _budget_error(error: BaseException) -> EvaluationBudgetExceeded | None:
    current: BaseException | None = error
    while current is not None:
        if isinstance(current, EvaluationBudgetExceeded):
            return current
        current = current.__cause__
    return None


EXPECTED_STATUS = {
    "answerable": AnswerStatus.SUPPORTED.value,
    "partial": AnswerStatus.PARTIAL.value,
    "conflict": AnswerStatus.CONFLICT.value,
    "insufficient_evidence": AnswerStatus.INSUFFICIENT_EVIDENCE.value,
    "context_required": "context_required",
}


def _read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise EvaluationError(f"{description} não encontrado: {path}.") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvaluationError(f"Não foi possível ler {description}: {path}.") from error
    if not isinstance(value, dict):
        raise EvaluationError(f"{description} deve conter um objeto JSON.")
    return value


def _load_cases(path: Path) -> list[dict[str, Any]]:
    data = _read_json(path, "Arquivo de casos")
    cases = data.get("cases")
    if data.get("format_version") != 1 or not isinstance(cases, list):
        raise EvaluationError(f"Arquivo de casos incompatível: {path}.")
    identifiers: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            raise EvaluationError(f"Caso inválido em {path}.")
        identifier = case.get("id")
        expected = case.get("expected")
        if (
            not isinstance(identifier, str)
            or not identifier
            or not isinstance(case.get("question"), str)
            or not isinstance(case.get("context"), dict)
            or not isinstance(expected, dict)
            or expected.get("status") not in EXPECTED_STATUS
            or not isinstance(expected.get("evidence"), list)
        ):
            raise EvaluationError(f"Contrato inválido no caso {identifier!r} de {path}.")
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise EvaluationError(f"Identificadores repetidos em {path}.")
    return cases


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return re.sub(r"\s+", " ", without_accents.casefold()).strip()


def _matches_expected(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    if (
        expected.get("document_id") != actual.get("document_id")
        or expected.get("page_number") != actual.get("page_number")
    ):
        return False
    expected_excerpt = expected.get("excerpt")
    actual_excerpt = actual.get("excerpt")
    if not isinstance(expected_excerpt, str) or not isinstance(actual_excerpt, str):
        return False
    expected_text = _normalized(expected_excerpt)
    actual_text = _normalized(actual_excerpt)
    return bool(expected_text and actual_text) and (
        expected_text in actual_text or actual_text in expected_text
    )


def _context(value: dict[str, Any]) -> RetrievalContext:
    return RetrievalContext(
        institution=value.get("institution"),
        course_level=value.get("course_level"),
        campus=value.get("campus"),
        modality=value.get("modality"),
    )


def _evidence_record(evidence: RetrievedEvidence) -> dict[str, Any]:
    return {
        "source_id": evidence.source_id,
        "document_id": evidence.document_id,
        "document_name": evidence.document_name,
        "page_number": evidence.page_number,
        "chunk_id": evidence.chunk_id,
        "excerpt": evidence.excerpt,
        "is_primary": evidence.is_primary,
        "distance": evidence.distance,
    }


def _answer_source_record(source: Any) -> dict[str, Any]:
    return {
        "source_id": source.source_id,
        "document_id": source.document_id,
        "document_name": source.document_name,
        "page_number": source.page_number,
        "chunk_id": source.chunk_id,
        "excerpt": source.excerpt,
    }


def _base_case_record(case: dict[str, Any], suite: str) -> dict[str, Any]:
    expected = case["expected"]
    return {
        "id": case["id"],
        "suite": suite,
        "category": case.get("category"),
        "question": case["question"],
        "context": case["context"],
        "expected": {
            "status": expected["status"],
            "answer_requirements": expected.get("answer_requirements", []),
            "evidence": expected["evidence"],
        },
        "actual": None,
        "checks": {},
        "technical_error": None,
        "manual_review": None,
    }


def _score_case(
    record: dict[str, Any],
    retrieval: RetrievalResult | None,
    answer: AnswerResult | None,
) -> None:
    expected = record["expected"]
    expected_status = EXPECTED_STATUS[expected["status"]]
    retrieved = (
        [_evidence_record(item) for item in retrieval.evidences] if retrieval else []
    )
    cited = [_answer_source_record(item) for item in answer.sources] if answer else []
    actual_status = answer.status.value if answer else record["actual"]["status"]
    expected_evidence = expected["evidence"]

    record["checks"] = {
        "status_correct": actual_status == expected_status,
        "retrieval_expected_total": len(expected_evidence),
        "retrieval_expected_found": sum(
            any(_matches_expected(item, source) for source in retrieved)
            for item in expected_evidence
        ),
        "citation_expected_total": len(expected_evidence),
        "citation_expected_found": sum(
            any(_matches_expected(item, source) for source in cited)
            for item in expected_evidence
        ),
        "citation_output_total": len(cited),
        "citation_output_relevant": sum(
            any(_matches_expected(item, source) for item in expected_evidence)
            for source in cited
        ),
        "abstention_correct": (
            actual_status == AnswerStatus.INSUFFICIENT_EVIDENCE.value
            and not cited
        )
        if expected["status"] == "insufficient_evidence"
        else None,
        "context_handling_correct": actual_status == "context_required"
        if expected["status"] == "context_required"
        else None,
    }


def _run_real_case(
    case: dict[str, Any],
    loaded: LoadedIndex,
    settings: Settings,
    model: InvokableModel,
    budget: CallBudget,
) -> dict[str, Any]:
    record = _base_case_record(case, "real")
    context = _context(case["context"])
    retrieval: RetrievalResult | None = None
    answer: AnswerResult | None = None
    try:
        if case["expected"]["status"] == "context_required":
            try:
                applicable_document_ids(settings, context)
            except ContextRequiredError as error:
                record["actual"] = {
                    "status": "context_required",
                    "message": str(error),
                    "retrieved": [],
                    "answer": None,
                    "sources": [],
                }
            else:
                record["actual"] = {
                    "status": "context_accepted",
                    "message": None,
                    "retrieved": [],
                    "answer": None,
                    "sources": [],
                }
            _score_case(record, None, None)
            return record

        budget.consume("embedding")
        retrieval = retrieve_evidence(case["question"], loaded, settings, context)
        answer = generate_answer(retrieval, model)
        record["actual"] = {
            "status": answer.status.value,
            "message": None,
            "retrieved": [_evidence_record(item) for item in retrieval.evidences],
            "answer": answer.answer,
            "sources": [_answer_source_record(item) for item in answer.sources],
            "limitations": list(retrieval.limitations),
        }
        _score_case(record, retrieval, answer)
    except EvaluationBudgetExceeded:
        raise
    except (
        ContextRequiredError,
        ContextNotCoveredError,
        IndexingError,
        RetrievalError,
        GenerationError,
        GenerationValidationError,
        ValueError,
    ) as error:
        exceeded = _budget_error(error)
        if exceeded is not None:
            raise exceeded
        record["technical_error"] = f"{type(error).__name__}: {error}"
    return record


def _synthetic_retrieval(case: dict[str, Any]) -> RetrievalResult:
    evidences = []
    for position, item in enumerate(case["expected"]["evidence"], start=1):
        source_id = item.get("source_id") or str(position)
        document_id = item["document_id"]
        evidences.append(
            RetrievedEvidence(
                source_id=source_id,
                document_id=document_id,
                document_name=item["document_name"],
                document_hash=sha256(document_id.encode("utf-8")).hexdigest(),
                page_number=item["page_number"],
                chunk_id=sha256(
                    f"{document_id}:{item['page_number']}:{item['excerpt']}".encode("utf-8")
                ).hexdigest(),
                excerpt=item["excerpt"],
                is_primary=True,
                distance=None,
            )
        )
    return RetrievalResult(
        question=case["question"],
        context=_context(case["context"]),
        evidences=tuple(evidences),
        limitations=(),
    )


def _run_synthetic_case(
    case: dict[str, Any], model: InvokableModel, budget: CallBudget
) -> dict[str, Any]:
    record = _base_case_record(case, "synthetic")
    retrieval = _synthetic_retrieval(case)
    try:
        answer = generate_answer(retrieval, model)
        record["actual"] = {
            "status": answer.status.value,
            "message": None,
            "retrieved": [_evidence_record(item) for item in retrieval.evidences],
            "answer": answer.answer,
            "sources": [_answer_source_record(item) for item in answer.sources],
            "limitations": [],
        }
        _score_case(record, retrieval, answer)
    except EvaluationBudgetExceeded:
        raise
    except (GenerationError, GenerationValidationError, ValueError) as error:
        exceeded = _budget_error(error)
        if exceeded is not None:
            raise exceeded
        record["technical_error"] = f"{type(error).__name__}: {error}"
    return record


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [record for record in records if record["technical_error"] is None]
    checks = [record["checks"] for record in completed]
    status_correct = sum(bool(item.get("status_correct")) for item in checks)
    retrieval_total = sum(item.get("retrieval_expected_total", 0) for item in checks)
    retrieval_found = sum(item.get("retrieval_expected_found", 0) for item in checks)
    citation_expected_total = sum(item.get("citation_expected_total", 0) for item in checks)
    citation_expected_found = sum(item.get("citation_expected_found", 0) for item in checks)
    citation_output_total = sum(item.get("citation_output_total", 0) for item in checks)
    citation_output_relevant = sum(
        item.get("citation_output_relevant", 0) for item in checks
    )
    abstentions = [
        item["abstention_correct"]
        for item in checks
        if item.get("abstention_correct") is not None
    ]
    contexts = [
        item["context_handling_correct"]
        for item in checks
        if item.get("context_handling_correct") is not None
    ]
    reviewed = [record["manual_review"] for record in records if record["manual_review"]]
    semantic_passed = sum(item["semantic_support"] for item in reviewed)
    conditions_passed = sum(item["requirements_preserved"] for item in reviewed)
    reviewed_citation_total = sum(
        len(record["actual"]["sources"])
        for record in records
        if record["manual_review"] and record["actual"]
    )
    reviewed_citation_supported = sum(
        record["manual_review"]["supported_citation_count"]
        for record in records
        if record["manual_review"]
    )
    return {
        "case_total": len(records),
        "completed_total": len(completed),
        "technical_error_total": len(records) - len(completed),
        "status_accuracy": _ratio(status_correct, len(completed)),
        "retrieval_recall": _ratio(retrieval_found, retrieval_total),
        "citation_recall": _ratio(citation_expected_found, citation_expected_total),
        "citation_label_precision": _ratio(
            citation_output_relevant, citation_output_total
        ),
        "citation_precision": _ratio(
            reviewed_citation_supported, reviewed_citation_total
        ),
        "abstention_accuracy": _ratio(sum(abstentions), len(abstentions)),
        "context_handling_accuracy": _ratio(sum(contexts), len(contexts)),
        "manual_review_total": len(reviewed),
        "manual_review_complete": len(reviewed) == len(records),
        "semantic_support_rate": _ratio(semantic_passed, len(reviewed)),
        "requirements_preservation_rate": _ratio(conditions_passed, len(reviewed)),
        "all_automated_checks_passed": bool(records)
        and not any(record["technical_error"] for record in records)
        and all(
            all(
                value is not False
                for key, value in record["checks"].items()
                if key.endswith("_correct")
            )
            and record["checks"].get("retrieval_expected_found", 0)
            == record["checks"].get("retrieval_expected_total", 0)
            and record["checks"].get("citation_expected_found", 0)
            == record["checks"].get("citation_expected_total", 0)
            for record in records
        ),
        "all_reviewed_checks_passed": bool(records)
        and len(reviewed) == len(records)
        and semantic_passed == len(records)
        and conditions_passed == len(records)
        and reviewed_citation_supported == reviewed_citation_total,
        "reviewed_citation_total": reviewed_citation_total,
        "reviewed_citation_supported": reviewed_citation_supported,
    }


def _file_sha256(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise EvaluationError(f"Não foi possível calcular o hash de {path}.") from error


def _source_fingerprint() -> str:
    source_dir = Path(__file__).resolve().parent
    digest = sha256()
    for path in sorted(source_dir.glob("*.py")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _git_metadata() -> dict[str, Any]:
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}
    return {"commit": commit, "dirty": dirty}


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            json.dump(value, temporary, ensure_ascii=False, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    except OSError as error:
        raise EvaluationError(f"Não foi possível gravar o relatório: {path}.") from error
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def run_evaluation(
    settings: Settings,
    real_cases_file: Path,
    synthetic_cases_file: Path,
    report_file: Path,
    *,
    max_provider_calls: int = 40,
    only_cases: set[str] | None = None,
    embeddings: Embeddings | None = None,
    model: InvokableModel | None = None,
) -> dict[str, Any]:
    """Executa uma tentativa por caso e grava dados locais para revisão humana."""
    if max_provider_calls <= 0:
        raise EvaluationError("O limite de chamadas externas deve ser maior que zero.")
    real_cases = _load_cases(real_cases_file)
    synthetic_cases = _load_cases(synthetic_cases_file)
    all_identifiers = {case["id"] for case in real_cases + synthetic_cases}
    if only_cases:
        unknown = sorted(only_cases - all_identifiers)
        if unknown:
            raise EvaluationError("Casos desconhecidos: " + ", ".join(unknown) + ".")
        real_cases = [case for case in real_cases if case["id"] in only_cases]
        synthetic_cases = [case for case in synthetic_cases if case["id"] in only_cases]

    try:
        active_embeddings = embeddings or create_embeddings(settings)
        loaded = load_active_index(settings, active_embeddings)
        active_model = model or create_chat_model(settings)
    except (IndexingError, GenerationError) as error:
        raise EvaluationError(
            "Não foi possível inicializar o índice ou os provedores da avaliação."
        ) from error
    budget = CallBudget(max_provider_calls)
    active_model = BudgetedModel(active_model, budget)
    records: list[dict[str, Any]] = []
    for case in real_cases:
        records.append(
            _run_real_case(case, loaded, settings, active_model, budget)
        )
    for case in synthetic_cases:
        records.append(_run_synthetic_case(case, active_model, budget))

    report = {
        "format_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "application_version": __version__,
            "git": _git_metadata(),
            "source_fingerprint_sha256": _source_fingerprint(),
            "system_prompt_sha256": sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
            "embedding_provider": settings.embedding_provider,
            "embedding_model": settings.embedding_model,
            "embedding_dimensions": settings.embedding_dimensions,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "llm_temperature": settings.llm_temperature,
            "llm_top_p": settings.llm_top_p,
            "llm_max_tokens": settings.llm_max_tokens,
            "retrieval_k": settings.retrieval_k,
            "retrieval_page_window": settings.retrieval_page_window,
            "retrieval_max_chunks": settings.retrieval_max_chunks,
            "active_index_id": loaded.manifest.get("index_id"),
            "indexed_documents": loaded.manifest.get("documents"),
            "case_files": {
                str(real_cases_file): _file_sha256(real_cases_file),
                str(synthetic_cases_file): _file_sha256(synthetic_cases_file),
            },
            "corpus_file": {
                "path": str(settings.corpus_file),
                "sha256": _file_sha256(settings.corpus_file),
            },
            "trial_count_per_case": 1,
            "semantic_judge": "revisão humana separada",
        },
        "provider_usage": {
            "max_calls": budget.limit,
            "embedding_calls": budget.embedding_calls,
            "generation_calls": budget.generation_calls,
            "total_calls": budget.total,
            "observed_cost": None,
            "cost_note": "A integração usada não informou custo monetário por chamada.",
        },
        "metrics": _aggregate(records),
        "cases": records,
    }
    _write_json_atomic(report_file, report)
    return report


def apply_manual_reviews(
    report_file: Path, reviews_file: Path, output_file: Path | None = None
) -> dict[str, Any]:
    """Anexa decisões humanas sem repetir chamadas aos provedores."""
    report = _read_json(report_file, "Relatório de avaliação")
    reviews = _read_json(reviews_file, "Revisão manual")
    if report.get("format_version") != 1 or not isinstance(report.get("cases"), list):
        raise EvaluationError("Relatório de avaliação incompatível.")
    if reviews.get("format_version") != 1 or not isinstance(reviews.get("cases"), list):
        raise EvaluationError("Arquivo de revisão manual incompatível.")
    by_id: dict[str, dict[str, Any]] = {}
    for review in reviews["cases"]:
        if (
            not isinstance(review, dict)
            or not isinstance(review.get("id"), str)
            or not isinstance(review.get("semantic_support"), bool)
            or not isinstance(review.get("requirements_preserved"), bool)
            or not isinstance(review.get("supported_citation_count"), int)
            or not isinstance(review.get("notes", ""), str)
        ):
            raise EvaluationError("Entrada inválida na revisão manual.")
        if review["id"] in by_id:
            raise EvaluationError(f"Revisão repetida para {review['id']}.")
        by_id[review["id"]] = review
    report_ids = {record["id"] for record in report["cases"]}
    unknown = sorted(set(by_id) - report_ids)
    if unknown:
        raise EvaluationError("Revisões sem caso correspondente: " + ", ".join(unknown) + ".")
    for record in report["cases"]:
        review = by_id.get(record["id"])
        if review and not 0 <= review["supported_citation_count"] <= len(
            (record.get("actual") or {}).get("sources", [])
        ):
            raise EvaluationError(
                f"Contagem de citações inválida na revisão de {record['id']}."
            )
        record["manual_review"] = (
            {
                "semantic_support": review["semantic_support"],
                "requirements_preserved": review["requirements_preserved"],
                "supported_citation_count": review["supported_citation_count"],
                "notes": review.get("notes", ""),
            }
            if review
            else None
        )
    report["manual_review"] = {
        "reviewer": reviews.get("reviewer", "não informado"),
        "reviewed_at": reviews.get("reviewed_at"),
        "reviews_file_sha256": _file_sha256(reviews_file),
    }
    report["metrics"] = _aggregate(report["cases"])
    _write_json_atomic(output_file or report_file, report)
    return report


def merge_retry_report(report_file: Path, retry_file: Path) -> dict[str, Any]:
    """Consolida reruns compatíveis sem repetir casos já concluídos."""
    report = _read_json(report_file, "Relatório de avaliação")
    retry = _read_json(retry_file, "Relatório de repetição")
    required_configuration = (
        "system_prompt_sha256",
        "embedding_model",
        "llm_model",
        "active_index_id",
        "case_files",
        "corpus_file",
    )
    if any(
        report.get("configuration", {}).get(key)
        != retry.get("configuration", {}).get(key)
        for key in required_configuration
    ):
        raise EvaluationError(
            "O relatório de repetição usa código, prompt, índice ou casos diferentes."
        )
    report_cases = report.get("cases")
    retry_cases = retry.get("cases")
    if not isinstance(report_cases, list) or not isinstance(retry_cases, list):
        raise EvaluationError("Relatório de avaliação incompatível.")
    by_id = {record.get("id"): record for record in report_cases}
    for record in retry_cases:
        identifier = record.get("id")
        if identifier not in by_id:
            raise EvaluationError(f"Caso de repetição desconhecido: {identifier}.")
        if record.get("technical_error") is not None:
            raise EvaluationError(f"A repetição de {identifier} ainda possui erro técnico.")
        by_id[identifier] = record
    report["cases"] = [by_id[record["id"]] for record in report_cases]
    previous_usage = report.get("provider_usage", {})
    retry_usage = retry.get("provider_usage", {})
    report["provider_usage"] = {
        "max_calls": previous_usage.get("max_calls", 0) + retry_usage.get("max_calls", 0),
        "embedding_calls": previous_usage.get("embedding_calls", 0)
        + retry_usage.get("embedding_calls", 0),
        "generation_calls": previous_usage.get("generation_calls", 0)
        + retry_usage.get("generation_calls", 0),
        "total_calls": previous_usage.get("total_calls", 0)
        + retry_usage.get("total_calls", 0),
        "observed_cost": None,
        "cost_note": "A integração usada não informou custo monetário por chamada.",
    }
    report.setdefault("reruns", []).append(
        {
            "merged_at": datetime.now(timezone.utc).isoformat(),
            "retry_report_sha256": _file_sha256(retry_file),
            "case_ids": [record["id"] for record in retry_cases],
            "previous_source_fingerprint_sha256": report["configuration"].get(
                "source_fingerprint_sha256"
            ),
        }
    )
    report["configuration"]["source_fingerprint_sha256"] = retry[
        "configuration"
    ].get("source_fingerprint_sha256")
    for record in report["cases"]:
        record["manual_review"] = None
    report.pop("manual_review", None)
    report["metrics"] = _aggregate(report["cases"])
    _write_json_atomic(report_file, report)
    return report

