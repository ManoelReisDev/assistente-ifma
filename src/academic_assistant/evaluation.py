"""Avaliação reproduzível do RAG, separada dos testes automatizados."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from importlib.metadata import version, PackageNotFoundError
import platform
from uuid import uuid4
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
    validate_precedence_metadata,
)
from academic_assistant.validation import (
    AnswerResult,
    AnswerStatus,
    GenerationValidationError,
    ModelDecision,
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
        if "evidence" in case:
            if not isinstance(case["evidence"], list):
                raise EvaluationError(f"Evidências de entrada inválidas no caso {identifier}.")
            for item in case["evidence"]:
                if not isinstance(item, dict) or any(
                    not isinstance(item.get(key), str) or not item[key].strip()
                    for key in ("source_id", "document_id", "document_name", "excerpt")
                ) or type(item.get("page_number")) is not int or item["page_number"] < 1:
                    raise EvaluationError(f"Evidência de entrada inválida no caso {identifier}.")
                try:
                    validate_precedence_metadata(item.get("publication_date"), item.get("precedence_group"))
                except RetrievalError as error:
                    raise EvaluationError(f"Metadados de precedência inválidos no caso {identifier}.") from error
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
        "publication_date": evidence.publication_date,
        "precedence_group": evidence.precedence_group,
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
        "case_sha256": _canonical_sha256(case),
        "generation_decisions": [],
        "retrieved": [],
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
        record["retrieved"] = [_evidence_record(item) for item in retrieval.evidences]
        answer = generate_answer(retrieval, model, trace=record["generation_decisions"])
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
    for position, item in enumerate(case.get("evidence", case["expected"]["evidence"]), start=1):
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
                publication_date=item.get("publication_date"),
                precedence_group=item.get("precedence_group"),
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
        record["retrieved"] = [_evidence_record(item) for item in retrieval.evidences]
        answer = generate_answer(retrieval, model, trace=record["generation_decisions"])
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
    configuration = _experiment_snapshot(settings, real_cases_file, synthetic_cases_file)
    real_cases = _load_cases(real_cases_file)
    synthetic_cases = _load_cases(synthetic_cases_file)
    all_identifiers = {case["id"] for case in real_cases + synthetic_cases}
    if len(all_identifiers) != len(real_cases) + len(synthetic_cases):
        raise EvaluationError("Identificadores repetidos entre os arquivos de casos.")
    if only_cases:
        unknown = sorted(only_cases - all_identifiers)
        if unknown:
            raise EvaluationError("Casos desconhecidos: " + ", ".join(unknown) + ".")
        real_cases = [case for case in real_cases if case["id"] in only_cases]
        synthetic_cases = [case for case in synthetic_cases if case["id"] in only_cases]

    run_id = uuid4().hex
    started_at = datetime.now(timezone.utc).isoformat()
    git_metadata = _git_metadata()
    try:
        active_embeddings = embeddings or create_embeddings(settings)
        loaded = load_active_index(settings, active_embeddings)
        active_model = model or create_chat_model(settings)
    except (IndexingError, GenerationError) as error:
        # No manifest is invented if initialization did not validate an index.
        stable = configuration == _experiment_snapshot(settings, real_cases_file, synthetic_cases_file)
        usage = {"max_calls": max_provider_calls, "embedding_calls": 0,
                 "generation_calls": 0, "total_calls": 0, "observed_cost": None}
        failed = {
            "format_version": 2, "completed": False,
            "initialization_error": f"{type(error).__name__}: {error}",
            "configuration_stable": stable,
            "runs": [{"run_id": run_id, "started_at": started_at,
                      "finished_at": datetime.now(timezone.utc).isoformat(),
                      "configuration": configuration,
                      "experiment_sha256": _canonical_sha256(configuration),
                      "provider_usage": usage, "metadata": {"git": git_metadata}}],
            "provider_usage": usage, "cases": [], "metrics": _aggregate([]),
        }
        _write_json_atomic(report_file, failed)
        raise EvaluationError(
            "Não foi possível inicializar o índice ou os provedores da avaliação."
        ) from error
    # Snapshot the validated manifest before the first counted invocation.
    configuration["index_manifest"] = json.loads(json.dumps(loaded.manifest))
    configuration["index_manifest_sha256"] = _canonical_sha256(loaded.manifest)
    budget = CallBudget(max_provider_calls)
    active_model = BudgetedModel(active_model, budget)
    records: list[dict[str, Any]] = []
    for case in real_cases:
        records.append(_run_real_case(case, loaded, settings, active_model, budget))
    for case in synthetic_cases:
        records.append(_run_synthetic_case(case, active_model, budget))
    final_configuration = _experiment_snapshot(settings, real_cases_file, synthetic_cases_file)
    final_configuration["index_manifest"] = loaded.manifest
    final_configuration["index_manifest_sha256"] = _canonical_sha256(loaded.manifest)
    if configuration != final_configuration:
        raise EvaluationError("Configuração/arquivos mudaram durante a execução; relatório não publicado.")
    for record in records:
        record["run_id"] = run_id
        record["result_sha256"] = _result_sha256(record)
    usage = {
        "max_calls": budget.limit,
        "embedding_calls": budget.embedding_calls,
        "generation_calls": budget.generation_calls,
        "total_calls": budget.total,
        "observed_cost": None,
        "cost_note": "A integração usada não informou custo monetário por chamada.",
    }
    run = {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "configuration": configuration,
        "experiment_sha256": _canonical_sha256(configuration),
        "provider_usage": usage,
        "metadata": {
            "git": git_metadata,
            "report_path": str(report_file),
            "only_cases": sorted(only_cases) if only_cases else None,
            "input_paths": {"real_cases": str(real_cases_file),
                            "synthetic_cases": str(synthetic_cases_file),
                            "corpus": str(settings.corpus_file),
                            "documents": str(settings.documents_dir),
                            "index": str(settings.index_dir)},
            "model_revision": None,
            "reproduction_note": "Nome solicitado; endpoint sem revisão imutável registrada. Hashes não autenticam os artefatos.",
        },
    }
    report = {
        "format_version": 2,
        "generated_at": run["finished_at"],
        "completed": True,
        "configuration_stable": True,
        "runs": [run],
        "provider_usage": dict(usage),
        "metrics": _aggregate(records),
        "cases": records,
    }
    _validate_report(report)
    _write_json_atomic(report_file, report)
    return report


def _canonical_sha256(value: Any) -> str:
    """Canonical JSON: UTF-8, sorted keys, compact separators, no NaN."""
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def _result_sha256(record: dict[str, Any]) -> str:
    # Only human review and the digest itself are excluded; includes checks/trace/errors.
    return _canonical_sha256({key: value for key, value in record.items()
                              if key not in {"manual_review", "result_sha256"}})


def _experiment_snapshot(settings: Settings, real: Path, synthetic: Path) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    dependencies = {}
    for package in ("langchain", "langchain-core", "langchain-chroma",
                    "langchain-nvidia-ai-endpoints", "langchain-text-splitters",
                    "chromadb", "pydantic", "pypdf", "onnxruntime"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = None
    parameters = {key: value for key, value in asdict(settings).items()
                  if not isinstance(value, Path)}
    # Observe current on-disk pointer/manifest even if the loaded index stays unchanged.
    index_files = {}
    active_path = settings.index_dir / "active.json"
    if active_path.is_file():
        index_files["active.json"] = _file_sha256(active_path)
        active = _read_json(active_path, "Referência do índice")
        identifier = active.get("index_id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[0-9TZ-]+-[a-f0-9]{12}", identifier):
            raise EvaluationError("Referência do índice inválida.")
        manifest_path = settings.index_dir / "versions" / identifier / "manifest.json"
        if manifest_path.is_file():
            index_files["manifest.json"] = _file_sha256(manifest_path)
    corpus = _read_json(settings.corpus_file, "Corpus")
    documents = {}
    selected = corpus.get("selection", {}).get("included_document_ids", [])
    for identifier in selected:
        path = settings.documents_dir / identifier
        if path.is_file():
            documents[identifier] = _file_sha256(path)
    return {
        "application_version": __version__,
        "source_fingerprint_sha256": _source_fingerprint(),
        "system_prompt_sha256": sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        "dependency_files": {name: _file_sha256(root / name) for name in ("pyproject.toml", "uv.lock")},
        "python_runtime": platform.python_version(),
        "dependencies": dependencies,
        "parameters": parameters,
        "structured_output": {"type": "json_schema", "strict": True,
                              "schema": ModelDecision.model_json_schema(),
                              "enable_thinking": False},
        "case_files": {"real": _file_sha256(real), "synthetic": _file_sha256(synthetic)},
        "corpus_sha256": _file_sha256(settings.corpus_file),
        "document_hashes": documents,
        "index_files": index_files,
    }


def _validate_review(review: dict[str, Any], record: dict[str, Any]) -> None:
    for key in ("id", "run_id", "result_sha256", "case_sha256"):
        if review.get(key) != record.get(key):
            raise EvaluationError(f"Revisão obsoleta/incompatível de {record['id']}: {key}.")
    ids = review.get("supported_source_ids")
    valid = {source["source_id"] for source in (record.get("actual") or {}).get("sources", [])}
    if (not isinstance(ids, list) or any(not isinstance(item, str) for item in ids)
            or len(set(ids)) != len(ids) or not set(ids) <= valid
            or type(review.get("supported_citation_count")) is not int
            or review["supported_citation_count"] != len(ids)
            or not isinstance(review.get("semantic_support"), bool)
            or not isinstance(review.get("requirements_preserved"), bool)
            or not isinstance(review.get("notes", ""), str)
            or not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip()
            or not isinstance(review.get("reviewed_at"), str)):
        raise EvaluationError(f"Revisão/fontes inválidas de {record['id']}.")
    try:
        date = datetime.fromisoformat(review["reviewed_at"].replace("Z", "+00:00"))
        if date.tzinfo is None:
            raise ValueError("timezone ausente")
    except ValueError as error:
        raise EvaluationError("Data da revisão inválida; informe timezone.") from error


def _validate_report(report: dict[str, Any]) -> None:
    if report.get("format_version") != 2:
        raise EvaluationError("Relatório legado/incompatível: execute nova avaliação em outro arquivo (formato 2).")
    runs, records = report.get("runs"), report.get("cases")
    if not isinstance(runs, list) or not runs or not isinstance(records, list):
        raise EvaluationError("Cadastro de execuções/casos inválido.")
    by_run = {}
    for run in runs:
        if (not isinstance(run, dict) or not isinstance(run.get("run_id"), str)
                or run["run_id"] in by_run or not isinstance(run.get("configuration"), dict)
                or run.get("experiment_sha256") != _canonical_sha256(run["configuration"])):
            raise EvaluationError("Execução/fingerprint inválido.")
        usage = run.get("provider_usage")
        if (not isinstance(usage, dict) or any(type(usage.get(key)) is not int or usage[key] < 0
                for key in ("max_calls", "embedding_calls", "generation_calls", "total_calls"))
                or usage["total_calls"] != usage["embedding_calls"] + usage["generation_calls"]
                or usage["total_calls"] > usage["max_calls"]):
            raise EvaluationError("Uso do provedor inválido.")
        by_run[run["run_id"]] = run
    if len({run["experiment_sha256"] for run in runs}) != 1:
        raise EvaluationError("Relatório contém experimentos incompatíveis.")
    seen = set()
    for record in records:
        if (not isinstance(record, dict) or not isinstance(record.get("id"), str)
                or record["id"] in seen or not isinstance(record.get("run_id"), str)
                or record["run_id"] not in by_run
                or record.get("result_sha256") != _result_sha256(record)
                or not isinstance(record.get("case_sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", record["case_sha256"])
                or not isinstance(record.get("checks"), dict)
                or "technical_error" not in record or "actual" not in record
                or "manual_review" not in record):
            raise EvaluationError("Caso, referência de execução ou hash inválido.")
        seen.add(record["id"])
        if record.get("manual_review"):
            _validate_review(record["manual_review"], record)


def apply_manual_reviews(
    report_file: Path, reviews_file: Path, output_file: Path | None = None
) -> dict[str, Any]:
    """Vincula decisões humanas à saída exata, preservando revisões existentes."""
    if output_file and output_file.resolve() == reviews_file.resolve():
        raise EvaluationError("Destino não pode sobrescrever o arquivo de revisões.")
    report = _read_json(report_file, "Relatório de avaliação")
    _validate_report(report)
    reviews = _read_json(reviews_file, "Revisão manual")
    if not report.get("cases"):
        raise EvaluationError("Execução sem resultados não pode receber revisão.")
    if reviews.get("format_version") != 2 or not isinstance(reviews.get("cases"), list):
        raise EvaluationError("Revisão legada/incompatível: use formato 2 vinculado ao novo resultado.")
    by_id = {record["id"]: record for record in report["cases"]}
    seen = set()
    for entry in reviews["cases"]:
        if not isinstance(entry, dict) or entry.get("id") not in by_id or entry["id"] in seen:
            raise EvaluationError("Revisão repetida ou sem caso correspondente.")
        seen.add(entry["id"])
        review = dict(entry)
        for key in ("reviewer", "reviewed_at"):
            review.setdefault(key, reviews.get(key))
        _validate_review(review, by_id[entry["id"]])
        by_id[entry["id"]]["manual_review"] = review
    report["metrics"] = _aggregate(report["cases"])
    _write_json_atomic(output_file or report_file, report)
    return report


def merge_retry_report(
    report_file: Path, retry_file: Path, output_file: Path | None = None
) -> dict[str, Any]:
    """Consolida somente execuções do mesmo experimento e mantém sua origem."""
    if output_file and output_file.resolve() == retry_file.resolve():
        raise EvaluationError("Destino não pode sobrescrever o relatório de repetição.")
    report = _read_json(report_file, "Relatório de avaliação")
    retry = _read_json(retry_file, "Relatório de repetição")
    _validate_report(report)
    _validate_report(retry)
    if not report.get("completed") or not retry.get("completed"):
        raise EvaluationError("Execução incompleta não pode ser consolidada.")
    previous = report["runs"][0]["configuration"]
    candidate = retry["runs"][0]["configuration"]
    differences = sorted(key for key in previous.keys() | candidate.keys()
                         if previous.get(key) != candidate.get(key))
    if differences:
        raise EvaluationError("Experimentos incompatíveis: " + ", ".join(differences) + ".")
    existing_runs = {run["run_id"] for run in report["runs"]}
    if existing_runs & {run["run_id"] for run in retry["runs"]}:
        raise EvaluationError("Repetição já aplicada; execuções não podem ser contabilizadas novamente.")
    by_id = {record["id"]: record for record in report["cases"]}
    substitutions = []
    for record in retry["cases"]:
        identifier = record["id"]
        if identifier not in by_id:
            raise EvaluationError(f"Caso de repetição desconhecido: {identifier}.")
        if record["case_sha256"] != by_id[identifier]["case_sha256"]:
            raise EvaluationError(f"Expectativa/caso incompatível: {identifier}.")
        if record.get("technical_error") is not None:
            raise EvaluationError(f"A repetição de {identifier} ainda possui erro técnico.")
        substitutions.append({"id": identifier, "previous": by_id[identifier],
                              "replacement": dict(record)})
        by_id[identifier] = dict(record, manual_review=None)
    report["cases"] = [by_id[record["id"]] for record in report["cases"]]
    report["runs"].extend(retry["runs"])
    report.setdefault("reruns", []).append({
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "retry_report_sha256": _file_sha256(retry_file),
        "run_ids": [run["run_id"] for run in retry["runs"]],
        "case_ids": [record["id"] for record in retry["cases"]],
        "substitutions": substitutions,
    })
    report["provider_usage"] = {
        key: sum(run["provider_usage"][key] for run in report["runs"])
        for key in ("max_calls", "embedding_calls", "generation_calls", "total_calls")
    }
    report["provider_usage"]["observed_cost"] = None
    report["metrics"] = _aggregate(report["cases"])
    _validate_report(report)
    _write_json_atomic(output_file or report_file, report)
    return report
