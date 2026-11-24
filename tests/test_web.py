"""Contrato HTTP da interface; nenhuma chamada externa ou chave real."""

from dataclasses import asdict
import json

import pytest

pytest.importorskip("fastapi", reason="Instale o extra web para testar a interface HTTP.")

from fastapi.testclient import TestClient

from academic_assistant.config import Settings
from academic_assistant.generation import GenerationError, GenerationProviderError
from academic_assistant.indexing import IndexingError
from academic_assistant.retrieval import (
    ContextNotCoveredError,
    ContextRequiredError,
    RetrievalError,
)
from academic_assistant.validation import (
    AnswerResult,
    AnswerSource,
    AnswerStatus,
    GenerationValidationError,
    INSUFFICIENT_EVIDENCE_MESSAGE,
    insufficient_evidence_result,
)
from academic_assistant.web import create_app


@pytest.fixture
def settings(tmp_path):
    corpus_file = tmp_path / "corpus.json"
    corpus_file.write_text(json.dumps({
        "format_version": 1,
        "documents": [
            {"document_id": "a", "document_hash": "hash-a", "selected": True,
             "institution_id": "IFMA", "course_level": "graduação", "campus": "Campus fictício"},
            {"document_id": "b", "document_hash": "hash-b", "selected": True,
             "institution_id": "IFMA", "course_level": "graduação", "modality": "Presencial"},
            {"document_id": "c", "selected": False, "course_level": "Não selecionado"},
        ],
        "selection": {"included_document_ids": ["a", "b"]},
    }), encoding="utf-8")
    return Settings(corpus_file=corpus_file, index_dir=tmp_path / "index")


def payload():
    return {"question": "Como solicitar a revisão fictícia?", "context": {
        "institution": "IFMA", "course_level": "graduação", "campus": None, "modality": None,
    }}


def supported_result(status=AnswerStatus.SUPPORTED):
    return AnswerResult(
        answer="A revisão fictícia pode ser solicitada em cinco dias úteis. [1]",
        status=status,
        sources=(AnswerSource(
            source_id="1", document_id="a", document_name="Regulamento fictício.pdf",
            page_number=7, chunk_id="ficticio-p7", excerpt="A revisão fictícia pode ser solicitada em cinco dias úteis.",
        ),),
    )


def test_context_only_reads_selected_inventory(settings):
    def never_call(*args):
        pytest.fail("Carregar a página/opções não pode consultar o RAG.")

    with TestClient(create_app(settings, answerer=never_call)) as client:
        response = client.get("/api/context")
        assert response.json() == {
            "institution": "IFMA", "course_levels": ["graduação"],
            "campuses": ["Campus fictício"], "modalities": ["Presencial"],
        }
        assert response.headers["cache-control"] == "no-store"
        assert client.get("/").status_code == 200
        for path in ("styles.css", "app.js", "assets/ifma.svg"):
            assert client.get(f"/static/{path}").status_code == 200
        assert client.get("/static/../../.env").status_code == 404
        assert client.get("/data/documents/a.pdf").status_code == 404


@pytest.mark.parametrize("status", list(AnswerStatus))
def test_answer_preserves_core_result_and_passes_context(settings, status):
    result = insufficient_evidence_result() if status == AnswerStatus.INSUFFICIENT_EVIDENCE else supported_result(status)
    received = []

    def answerer(question, context, active_settings):
        received.append((question, context, active_settings))
        return result

    with TestClient(create_app(settings, answerer=answerer)) as client:
        response = client.post("/api/ask", json=payload())
        assert response.status_code == 200
        expected = asdict(result)
        expected["sources"] = [asdict(source) for source in result.sources]
        assert response.json() == expected
        assert response.headers["cache-control"] == "no-store"
        assert "script-src 'self'" in response.headers["content-security-policy"]
    question, context, active_settings = received[0]
    assert question == payload()["question"]
    assert context.institution == "IFMA"
    assert context.course_level == "graduação"
    assert context.campus is None
    assert active_settings is settings


@pytest.mark.parametrize("change", [
    {"question": "  "}, {"question": "x" * 4001}, {"question": None},
    {"context": {}}, {"context": {"course_level": "   "}},
    {"context": {"course_level": "graduação", "institution": "Outra"}},
    {"history": [{"content": "Dado sensível"}]},
])
def test_invalid_requests_do_not_reach_rag_or_echo_input(settings, change):
    def never_call(*args):
        pytest.fail("Entrada inválida chegou ao núcleo.")

    with TestClient(create_app(settings, answerer=never_call)) as client:
        response = client.post("/api/ask", json=payload() | change)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert "Dado sensível" not in response.text
    assert "sources" not in response.json()


def test_trims_question_and_optional_context(settings):
    received = []

    def answerer(question, context, settings):
        received.append((question, context))
        return insufficient_evidence_result()

    data = payload()
    data["question"] = "  Pergunta fictícia  "
    data["context"].update(campus="  ", modality="  ")
    with TestClient(create_app(settings, answerer=answerer)) as client:
        assert client.post("/api/ask", json=data).status_code == 200
    assert received[0][0] == "Pergunta fictícia"
    assert received[0][1].campus is None
    assert received[0][1].modality is None


@pytest.mark.parametrize("error,status,code", [
    (ContextRequiredError("Informe nível do curso."), 422, "invalid_context"),
    (ContextNotCoveredError("Contexto não coberto."), 422, "invalid_context"),
    (IndexingError("/private/corpus.json"), 503, "index_unavailable"),
    (RetrievalError("falha interna"), 502, "retrieval_failed"),
    (GenerationValidationError("saída inventada"), 502, "invalid_generation"),
    (GenerationProviderError("erro do endpoint"), 502, "provider_failed"),
    (GenerationError("chave ausente"), 503, "generation_unavailable"),
])
def test_technical_errors_are_not_abstention(settings, error, status, code):
    def fail(*args):
        raise error

    with TestClient(create_app(settings, answerer=fail)) as client:
        response = client.post("/api/ask", json=payload())
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "sources" not in response.json()
    assert INSUFFICIENT_EVIDENCE_MESSAGE not in response.text
    assert "/private/" not in response.text


def test_missing_inventory_returns_actionable_error(tmp_path):
    with TestClient(create_app(Settings(corpus_file=tmp_path / "absent.json"))) as client:
        response = client.get("/api/context")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "corpus_unavailable"
    assert str(tmp_path) not in response.text


@pytest.mark.parametrize("field", ["campus", "modality"])
def test_context_rejects_invalid_inventory_scope(settings, field):
    corpus = json.loads(settings.corpus_file.read_text())
    corpus["documents"][0][field] = ["valor fictício inválido"]
    settings.corpus_file.write_text(json.dumps(corpus))

    with TestClient(create_app(settings)) as client:
        response = client.get("/api/context")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "corpus_unavailable"
    assert str(settings.corpus_file) not in response.text


def test_api_runs_real_query_pipeline_offline(tmp_path):
    # Reutiliza o índice sintético já empregado nos testes do núcleo.
    from test_query import DeterministicEmbeddings, FakeModel, make_persisted_index
    from academic_assistant.query import answer_question

    settings, builder = make_persisted_index(tmp_path)
    embeddings = DeterministicEmbeddings()
    model = FakeModel({
        "status": "supported", "answer": "A revisão fictícia pode ser solicitada em cinco dias úteis.",
        "source_ids": ["1"], "unsupported_parts": [],
    })

    def answerer(question, context, settings):
        return answer_question(question, context, settings, embeddings=embeddings, model=model)

    with TestClient(create_app(settings, answerer=answerer)) as client:
        for _ in range(2):
            response = client.post("/api/ask", json=payload())
            assert response.status_code == 200
            source = response.json()["sources"][0]
            assert source["page_number"] == 7
            assert source["document_name"] == "Regulamento fictício.pdf"
            assert source["excerpt"] == "A revisão fictícia pode ser solicitada em cinco dias úteis."
        model.output = {"status": "supported", "answer": "Regra inventada.", "source_ids": ["999"], "unsupported_parts": []}
        assert client.post("/api/ask", json=payload()).json()["error"]["code"] == "invalid_generation"
    assert builder.document_calls == 1
    assert embeddings.document_calls == 0
    assert embeddings.query_calls == 3
