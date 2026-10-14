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
    run_evaluation(
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
            "format_version": 1,
            "reviewer": "teste automatizado",
            "reviewed_at": "2026-10-13T00:00:00Z",
            "cases": [
                {
                    "id": identifier,
                    "semantic_support": True,
                    "requirements_preserved": True,
                    "supported_citation_count": 1 if identifier == "REAL-001" else 2,
                    "notes": "Regra fictícia revisada.",
                }
                for identifier in ("REAL-001", "SYN-001")
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

