"""A avaliação automatizada usa somente regras e documentos fictícios."""

from hashlib import sha256
import json
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from academic_assistant import evaluation
from academic_assistant.config import Settings
from academic_assistant.evaluation import (
    EvaluationBudgetExceeded,
    apply_manual_reviews,
    merge_retry_report,
    run_evaluation,
)
from academic_assistant.indexing import LoadedIndex


class UnusedEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise AssertionError("não deve indexar documentos")

    def embed_query(self, text: str) -> list[float]:
        return [1.0, 0.0]


class FakeStore:
    def __init__(self, document: Document) -> None:
        self.document = document

    def similarity_search_with_score(self, query, k, filter):
        return [(self.document, 0.1)]

    def get(self, **kwargs):
        return {"documents": [], "metadatas": []}


class QuestionAwareModel:
    def __init__(self) -> None:
        self.calls = 0

    def bind(self, **kwargs):
        return self

    def invoke(self, messages, **kwargs):
        self.calls += 1
        content = messages[-1].content
        if "prazos fictícios" in content:
            return {
                "status": "conflict",
                "answer": "Uma fonte prevê dez dias e outra prevê sete dias.",
                "source_ids": ["SYN-A", "SYN-B"],
                "unsupported_parts": [],
            }
        return {
            "status": "supported",
            "answer": "A regra fictícia permite o pedido em cinco dias.",
            "source_ids": ["1"],
            "unsupported_parts": [],
        }


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _evaluation_fixture(tmp_path: Path, monkeypatch):
    settings = Settings(
        documents_dir=tmp_path / "documents",
        index_dir=tmp_path / "index",
        corpus_file=tmp_path / "corpus.json",
        embedding_provider="test",
        embedding_model="test-embedding",
        embedding_dimensions=2,
        llm_provider="test",
        llm_model="test-llm",
        retrieval_k=1,
        retrieval_page_window=0,
        retrieval_max_chunks=1,
    )
    settings.documents_dir.mkdir()
    document_hash = sha256(b"regra ficticia").hexdigest()
    _write_json(
        settings.corpus_file,
        {
            "format_version": 1,
            "documents": [
                {
                    "document_id": "regra.pdf",
                    "document_name": "Regra fictícia",
                    "document_hash": document_hash,
                    "institution_id": "IFMA",
                    "course_level": "graduação",
                    "selected": True,
                }
            ],
            "selection": {"included_document_ids": ["regra.pdf"]},
        },
    )
    indexed = Document(
        page_content="A regra fictícia permite o pedido em cinco dias.",
        metadata={
            "document_id": "regra.pdf",
            "document_name": "Regra fictícia",
            "document_hash": document_hash,
            "page_number": 2,
            "chunk_id": "chunk-2",
        },
    )
    loaded = LoadedIndex(
        store=FakeStore(indexed),
        manifest={"index_id": "indice-ficticio", "documents": []},
    )
    monkeypatch.setattr(evaluation, "load_active_index", lambda *args: loaded)

    real_cases = tmp_path / "real.json"
    _write_json(
        real_cases,
        {
            "format_version": 1,
            "cases": [
                {
                    "id": "REAL-001",
                    "category": "answerable",
                    "question": "Qual é o prazo fictício?",
                    "context": {"institution": "IFMA", "course_level": "graduação"},
                    "expected": {
                        "status": "answerable",
                        "answer_requirements": ["informar cinco dias"],
                        "evidence": [
                            {
                                "document_id": "regra.pdf",
                                "document_name": "Regra fictícia",
                                "page_number": 2,
                                "excerpt": "A regra fictícia permite o pedido em cinco dias.",
                            }
                        ],
                    },
                }
            ],
        },
    )
    synthetic_cases = tmp_path / "synthetic.json"
    _write_json(
        synthetic_cases,
        {
            "format_version": 1,
            "cases": [
                {
                    "id": "SYN-001",
                    "category": "conflict",
                    "question": "Quais são os prazos fictícios?",
                    "context": {"institution": "Fictícia", "course_level": "graduação"},
                    "expected": {
                        "status": "conflict",
                        "answer_requirements": ["apresentar os dois prazos"],
                        "evidence": [
                            {
                                "source_id": "SYN-A",
                                "document_id": "a.pdf",
                                "document_name": "A",
                                "page_number": 1,
                                "excerpt": "O prazo fictício é de dez dias.",
                            },
                            {
                                "source_id": "SYN-B",
                                "document_id": "b.pdf",
                                "document_name": "B",
                                "page_number": 3,
                                "excerpt": "O prazo fictício é de sete dias.",
                            },
                        ],
                    },
                }
            ],
        },
    )
    return settings, real_cases, synthetic_cases


def test_evaluation_measures_retrieval_citations_and_status(tmp_path: Path, monkeypatch) -> None:
    settings, real_cases, synthetic_cases = _evaluation_fixture(tmp_path, monkeypatch)
    report_file = tmp_path / "results.local.json"
    model = QuestionAwareModel()

    report = run_evaluation(
        settings,
        real_cases,
        synthetic_cases,
        report_file,
        max_provider_calls=4,
        embeddings=UnusedEmbeddings(),
        model=model,
    )

    assert report_file.is_file()
    assert report["provider_usage"]["embedding_calls"] == 1
    assert report["provider_usage"]["generation_calls"] == 2
    assert report["metrics"]["status_accuracy"] == 1.0
    assert report["metrics"]["retrieval_recall"] == 1.0
    assert report["metrics"]["citation_recall"] == 1.0
    assert report["metrics"]["citation_label_precision"] == 1.0
    assert report["metrics"]["citation_precision"] is None
    assert report["metrics"]["all_automated_checks_passed"] is True
    assert model.calls == 2


def test_evaluation_stops_before_exceeding_call_budget(tmp_path: Path, monkeypatch) -> None:
    settings, real_cases, synthetic_cases = _evaluation_fixture(tmp_path, monkeypatch)

    with pytest.raises(EvaluationBudgetExceeded, match="Limite"):
        run_evaluation(
            settings,
            real_cases,
            synthetic_cases,
            tmp_path / "results.json",
            max_provider_calls=1,
            embeddings=UnusedEmbeddings(),
            model=QuestionAwareModel(),
        )


def test_evaluation_wraps_index_initialization_failure(tmp_path: Path, monkeypatch) -> None:
    settings, real_cases, synthetic_cases = _evaluation_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(
        evaluation,
        "load_active_index",
        lambda *args: (_ for _ in ()).throw(
            evaluation.IndexingError("índice fictício indisponível")
        ),
    )

    with pytest.raises(evaluation.EvaluationError, match="inicializar"):
        run_evaluation(
            settings,
            real_cases,
            synthetic_cases,
            tmp_path / "results.json",
            embeddings=UnusedEmbeddings(),
            model=QuestionAwareModel(),
        )


def test_manual_review_updates_metrics_without_provider_calls(tmp_path: Path, monkeypatch) -> None:
    settings, real_cases, synthetic_cases = _evaluation_fixture(tmp_path, monkeypatch)
    report_file = tmp_path / "results.local.json"
    report = run_evaluation(
        settings,
        real_cases,
        synthetic_cases,
        report_file,
        embeddings=UnusedEmbeddings(),
        model=QuestionAwareModel(),
    )
    reviews_file = tmp_path / "reviews.local.json"
    _write_json(
        reviews_file,
        {
            "format_version": 2,
            "reviewer": "teste automatizado",
            "reviewed_at": "2026-10-13T00:00:00Z",
            "cases": [
                {
                    "id": record["id"],
                    "run_id": record["run_id"],
                    "result_sha256": record["result_sha256"],
                    "case_sha256": record["case_sha256"],
                    "supported_source_ids": [item["source_id"] for item in record["actual"]["sources"]],
                    "semantic_support": True,
                    "requirements_preserved": True,
                    "supported_citation_count": len(record["actual"]["sources"]),
                    "notes": "Regra fictícia revisada.",
                }
                for record in report["cases"]
            ],
        },
    )

    reviewed = apply_manual_reviews(report_file, reviews_file)

    assert reviewed["metrics"]["manual_review_complete"] is True
    assert reviewed["metrics"]["semantic_support_rate"] == 1.0
    assert reviewed["metrics"]["requirements_preservation_rate"] == 1.0
    assert reviewed["metrics"]["citation_precision"] == 1.0
    assert reviewed["metrics"]["all_reviewed_checks_passed"] is True


def test_compatible_retry_replaces_case_and_accumulates_usage(tmp_path: Path, monkeypatch) -> None:
    settings, real_cases, synthetic_cases = _evaluation_fixture(tmp_path, monkeypatch)
    report_file = tmp_path / "results.local.json"
    retry_file = tmp_path / "retry.local.json"
    run_evaluation(
        settings,
        real_cases,
        synthetic_cases,
        report_file,
        embeddings=UnusedEmbeddings(),
        model=QuestionAwareModel(),
    )
    run_evaluation(
        settings,
        real_cases,
        synthetic_cases,
        retry_file,
        only_cases={"REAL-001"},
        embeddings=UnusedEmbeddings(),
        model=QuestionAwareModel(),
    )

    merged = merge_retry_report(report_file, retry_file)

    assert merged["metrics"]["case_total"] == 2
    assert merged["metrics"]["technical_error_total"] == 0
    assert merged["provider_usage"]["total_calls"] == 5
    assert merged["reruns"][0]["case_ids"] == ["REAL-001"]



def _run_fixture(tmp_path, monkeypatch):
    settings, real, synthetic = _evaluation_fixture(tmp_path, monkeypatch)
    path = tmp_path / "base.json"
    report = run_evaluation(settings, real, synthetic, path,
                            embeddings=UnusedEmbeddings(), model=QuestionAwareModel())
    return settings, real, synthetic, path, report


def _reviews(report):
    return {"format_version": 2, "reviewer": "Revisor fictício",
            "reviewed_at": "2026-10-14T00:00:00Z", "cases": [
                {key: record[key] for key in ("id", "run_id", "result_sha256", "case_sha256")}
                | {"semantic_support": True, "requirements_preserved": True,
                   "supported_source_ids": [s["source_id"] for s in record["actual"]["sources"]],
                   "supported_citation_count": len(record["actual"]["sources"])}
                for record in report["cases"]]}


def test_review_and_merge_preserve_sources_origins_and_unchanged_reviews(tmp_path, monkeypatch):
    settings, real, synthetic, path, report = _run_fixture(tmp_path, monkeypatch)
    review_path = tmp_path / "reviews.json"
    _write_json(review_path, _reviews(report))
    reviewed_path = tmp_path / "reviewed.json"
    reviewed = apply_manual_reviews(path, review_path, reviewed_path)
    original_bytes = path.read_bytes()
    reviewed_bytes = reviewed_path.read_bytes()
    retry_path = tmp_path / "retry.json"
    retry = run_evaluation(settings, real, synthetic, retry_path, only_cases={"REAL-001"},
                           max_provider_calls=3, embeddings=UnusedEmbeddings(), model=QuestionAwareModel())
    merged_path = tmp_path / "merged.json"
    merged = merge_retry_report(reviewed_path, retry_path, merged_path)
    assert path.read_bytes() == original_bytes
    assert reviewed_path.read_bytes() == reviewed_bytes
    assert merged["cases"][0]["manual_review"] is None
    assert merged["cases"][0]["run_id"] == retry["cases"][0]["run_id"]
    assert merged["cases"][1] == reviewed["cases"][1]
    assert len(merged["runs"]) == 2
    assert merged["reruns"][0]["substitutions"][0]["previous"] == reviewed["cases"][0]
    before = merged_path.read_bytes()
    with pytest.raises(evaluation.EvaluationError, match="já aplicada"):
        merge_retry_report(merged_path, retry_path)
    assert merged_path.read_bytes() == before
    with pytest.raises(evaluation.EvaluationError, match="obsoleta"):
        apply_manual_reviews(merged_path, review_path)
    assert merged_path.read_bytes() == before


@pytest.mark.parametrize("field", ["source_fingerprint_sha256", "system_prompt_sha256",
    "dependency_files", "python_runtime", "dependencies", "structured_output",
    "case_files", "corpus_sha256", "document_hashes", "index_manifest_sha256"])
def test_merge_rejects_each_experiment_difference(tmp_path, monkeypatch, field):
    _, _, _, path, report = _run_fixture(tmp_path, monkeypatch)
    retry_path = tmp_path / "retry.json"
    report["runs"][0]["configuration"][field] = "different"
    report["runs"][0]["experiment_sha256"] = evaluation._canonical_sha256(report["runs"][0]["configuration"])
    _write_json(retry_path, report)
    original = path.read_bytes()
    with pytest.raises(evaluation.EvaluationError, match=field):
        merge_retry_report(path, retry_path)
    assert path.read_bytes() == original


@pytest.mark.parametrize("field", ["embedding_dimensions", "llm_temperature", "llm_top_p",
    "llm_max_tokens", "retrieval_k", "retrieval_page_window", "retrieval_max_chunks",
    "chunk_size", "chunk_overlap", "collection_name"])
def test_merge_rejects_parameter_difference(tmp_path, monkeypatch, field):
    _, _, _, path, report = _run_fixture(tmp_path, monkeypatch)
    run = report["runs"][0]
    run["configuration"]["parameters"][field] = "different"
    run["experiment_sha256"] = evaluation._canonical_sha256(run["configuration"])
    retry = tmp_path / "retry.json"
    _write_json(retry, report)
    with pytest.raises(evaluation.EvaluationError, match="parameters"):
        merge_retry_report(path, retry)


@pytest.mark.parametrize("mutation", ["missing_run", "result_hash", "case_hash", "duplicate", "legacy"])
def test_invalid_provenance_is_rejected(tmp_path, monkeypatch, mutation):
    _, _, _, path, report = _run_fixture(tmp_path, monkeypatch)
    if mutation == "missing_run":
        report["cases"][0]["run_id"] = "unknown"
    elif mutation == "result_hash":
        report["cases"][0]["actual"]["answer"] = "adulterada"
    elif mutation == "case_hash":
        report["cases"][0]["case_sha256"] = "wrong"
    elif mutation == "duplicate":
        report["cases"].append(report["cases"][0])
    else:
        report["format_version"] = 1
    _write_json(path, report)
    before = path.read_bytes()
    with pytest.raises(evaluation.EvaluationError):
        merge_retry_report(path, path)
    assert path.read_bytes() == before


@pytest.mark.parametrize("mutation", ["unknown_source", "duplicate_source", "count", "boolean_count",
                                       "result", "expectation", "reviewer", "date"])
def test_review_rejects_invalid_binding_and_sources(tmp_path, monkeypatch, mutation):
    _, _, _, path, report = _run_fixture(tmp_path, monkeypatch)
    reviews = _reviews(report)
    entry = reviews["cases"][0]
    if mutation == "unknown_source":
        entry["supported_source_ids"] = ["unknown"]
    elif mutation == "duplicate_source":
        entry["supported_source_ids"] = ["1", "1"]
        entry["supported_citation_count"] = 2
    elif mutation == "count":
        entry["supported_citation_count"] = 0
    elif mutation == "boolean_count":
        entry["supported_citation_count"] = True
    elif mutation == "result":
        entry["result_sha256"] = "0" * 64
    elif mutation == "expectation":
        entry["case_sha256"] = "0" * 64
    elif mutation == "reviewer":
        reviews["reviewer"] = ""
    else:
        reviews["reviewed_at"] = "yesterday"
    review_path = tmp_path / "review.json"
    _write_json(review_path, reviews)
    before = path.read_bytes()
    with pytest.raises(evaluation.EvaluationError):
        apply_manual_reviews(path, review_path)
    assert path.read_bytes() == before


def test_snapshot_precedes_calls_and_mutation_prevents_publication(tmp_path, monkeypatch):
    settings, real, synthetic = _evaluation_fixture(tmp_path, monkeypatch)
    path = tmp_path / "report.json"
    path.write_text("previous report")
    calls = []
    original = evaluation._experiment_snapshot
    def snapshot(*args):
        calls.append("snapshot")
        return original(*args)
    monkeypatch.setattr(evaluation, "_experiment_snapshot", snapshot)
    class MutatingModel(QuestionAwareModel):
        def invoke(self, messages, **kwargs):
            assert calls == ["snapshot"]
            settings.corpus_file.write_text(settings.corpus_file.read_text() + "\n")
            return super().invoke(messages, **kwargs)
    with pytest.raises(evaluation.EvaluationError, match="mudaram"):
        run_evaluation(settings, real, synthetic, path, only_cases={"REAL-001"},
                       embeddings=UnusedEmbeddings(), model=MutatingModel())
    assert path.read_text() == "previous report"
    assert calls == ["snapshot", "snapshot"]


def test_atomic_write_failure_preserves_report(tmp_path, monkeypatch):
    path = tmp_path / "report.json"
    path.write_text("original")
    def fail(*args):
        raise OSError("falha fictícia")
    monkeypatch.setattr(evaluation.os, "replace", fail)
    with pytest.raises(evaluation.EvaluationError, match="gravar"):
        evaluation._write_json_atomic(path, {"new": True})
    assert path.read_text() == "original"
    assert list(tmp_path.iterdir()) == [path]


def test_canonical_hash_excludes_review_but_covers_trace_and_expectations(tmp_path, monkeypatch):
    _, _, _, _, report = _run_fixture(tmp_path, monkeypatch)
    record = report["cases"][0]
    assert evaluation._canonical_sha256({"a": 1, "b": 2}) == evaluation._canonical_sha256({"b": 2, "a": 1})
    assert record["generation_decisions"][0]["purpose"] == "initial"
    assert record["generation_decisions"][0]["selected"] is True
    record["manual_review"] = {"arbitrary": True}
    assert evaluation._result_sha256(record) == record["result_sha256"]
    record["generation_decisions"][0]["selected"] = False
    assert evaluation._result_sha256(record) != record["result_sha256"]


def test_initialization_failure_records_known_snapshot_without_inventing_manifest(tmp_path, monkeypatch):
    settings, real, synthetic = _evaluation_fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(evaluation, "load_active_index", lambda *args: (_ for _ in ()).throw(evaluation.IndexingError("fictício")))
    path = tmp_path / "failure.json"
    with pytest.raises(evaluation.EvaluationError, match="inicializar"):
        run_evaluation(settings, real, synthetic, path, embeddings=UnusedEmbeddings(), model=QuestionAwareModel())
    report = json.loads(path.read_text())
    evaluation._validate_report(report)
    assert report["completed"] is False
    assert report["provider_usage"]["total_calls"] == 0
    assert "index_manifest" not in report["runs"][0]["configuration"]
    assert report["initialization_error"]


def test_error_results_keep_run_and_retrieval_and_trace(tmp_path, monkeypatch):
    settings, real, synthetic = _evaluation_fixture(tmp_path, monkeypatch)
    class Broken(QuestionAwareModel):
        def invoke(self, messages, **kwargs):
            return "invalid fictitious JSON"
    report = run_evaluation(settings, real, synthetic, tmp_path / "errors.json",
                            embeddings=UnusedEmbeddings(), model=Broken())
    assert report["metrics"]["technical_error_total"] == 2
    for record in report["cases"]:
        assert record["run_id"] == report["runs"][0]["run_id"]
        assert record["result_sha256"] == evaluation._result_sha256(record)
        assert record["retrieved"]
        assert record["generation_decisions"][0]["validation_error"]


def test_cli_review_and_merge_dispatch_separate_output(tmp_path, monkeypatch, capsys):
    from academic_assistant.cli import main
    calls = []
    def review(report, reviews, output):
        calls.append((report, reviews, output))
        return {"metrics": {"manual_review_total": 1, "case_total": 1,
                            "semantic_support_rate": 1, "requirements_preservation_rate": 1,
                            "manual_review_complete": True}}
    def merge(report, retry, output):
        calls.append((report, retry, output))
        return {"metrics": {"completed_total": 1, "case_total": 1, "technical_error_total": 0}}
    monkeypatch.setattr(evaluation, "apply_manual_reviews", review)
    monkeypatch.setattr(evaluation, "merge_retry_report", merge)
    output = tmp_path / "output.json"
    assert main(["evaluate-review", "--output", str(output)]) == 0
    assert main(["evaluate-merge", "--retry", "retry.json", "--output", str(output)]) == 0
    assert [call[2] for call in calls] == [output, output]
