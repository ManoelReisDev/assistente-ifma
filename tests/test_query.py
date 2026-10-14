"""O fluxo integrado deste arquivo usa somente documentos e regras fictícios."""

from hashlib import sha256
import json
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from academic_assistant.config import Settings
from academic_assistant.indexing import rebuild_index
from academic_assistant.query import answer_question
from academic_assistant.retrieval import RetrievalContext, RetrievalResult
from academic_assistant.retrieval import ContextRequiredError
from academic_assistant.validation import AnswerStatus, INSUFFICIENT_EVIDENCE_MESSAGE


class DeterministicEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions
        self.document_calls = 0
        self.query_calls = 0

    def _vector(self, text: str) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        return [(digest[index % len(digest)] + 1) / 256 for index in range(self.dimensions)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += 1
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls += 1
        return self._vector(text)


class FakeModel:
    def __init__(self, output: dict) -> None:
        self.output = output
        self.calls = 0

    def bind(self, **kwargs):
        return self

    def invoke(self, input, **kwargs):
        self.calls += 1
        return self.output


def make_persisted_index(tmp_path: Path):
    settings = Settings(
        documents_dir=tmp_path / "documents",
        index_dir=tmp_path / "index",
        corpus_file=tmp_path / "corpus.json",
        embedding_provider="test",
        embedding_model="deterministic-test",
        embedding_dimensions=8,
        collection_name="query-test",
        retrieval_k=1,
        retrieval_page_window=0,
        retrieval_max_chunks=1,
    )
    settings.documents_dir.mkdir()
    content = b"documento academico inteiramente ficticio"
    document_hash = sha256(content).hexdigest()
    (settings.documents_dir / "regra.pdf").write_bytes(content)
    settings.corpus_file.write_text(
        json.dumps(
            {
                "format_version": 1,
                "documents": [
                    {
                        "document_id": "regra.pdf",
                        "document_name": "Regulamento fictício.pdf",
                        "document_hash": document_hash,
                        "institution_id": "IFMA",
                        "course_level": "graduação",
                        "selected": True,
                        "applicability_limits": "Vigência fictícia não comprovada.",
                    }
                ],
                "selection": {"included_document_ids": ["regra.pdf"]},
            }
        ),
        encoding="utf-8",
    )
    chunk = Document(
        page_content="A revisão fictícia pode ser solicitada em cinco dias úteis.",
        metadata={
            "document_id": "regra.pdf",
            "document_name": "Regulamento fictício.pdf",
            "document_hash": document_hash,
            "page_number": 7,
            "chunk_id": "chunk-ficticio-7",
        },
    )
    builder_embeddings = DeterministicEmbeddings()
    rebuild_index([chunk], builder_embeddings, settings)
    return settings, builder_embeddings


def test_query_reloads_index_and_returns_validated_answer(tmp_path: Path) -> None:
    settings, builder_embeddings = make_persisted_index(tmp_path)
    query_embeddings = DeterministicEmbeddings()
    model = FakeModel(
        {
            "status": "supported",
            "answer": "A revisão fictícia pode ser solicitada em cinco dias úteis.",
            "source_ids": ["1"],
            "unsupported_parts": [],
        }
    )

    result = answer_question(
        "Qual é o prazo fictício para revisão?",
        RetrievalContext(institution="IFMA", course_level="graduação"),
        settings,
        embeddings=query_embeddings,
        model=model,
    )

    assert result.status is AnswerStatus.SUPPORTED
    assert result.sources[0].document_name == "Regulamento fictício.pdf"
    assert result.sources[0].page_number == 7
    assert result.sources[0].excerpt.startswith("A revisão fictícia")
    assert "[1]" in result.answer
    assert "Limitação do corpus:" in result.answer
    assert builder_embeddings.document_calls == 1
    assert query_embeddings.document_calls == 0
    assert query_embeddings.query_calls == 1
    assert model.calls == 1


def test_query_does_not_create_chat_model_without_evidence(monkeypatch) -> None:
    from academic_assistant import query

    retrieval = RetrievalResult(
        question="Pergunta fictícia sem evidência",
        context=RetrievalContext(institution="IFMA", course_level="graduação"),
        evidences=(),
        limitations=(),
    )
    monkeypatch.setattr(query, "retrieve_from_active_index", lambda *args: retrieval)
    monkeypatch.setattr(
        query,
        "create_chat_model",
        lambda _: (_ for _ in ()).throw(AssertionError("LLM não deveria ser criado")),
    )

    result = answer_question(
        retrieval.question,
        retrieval.context,
        Settings(),
        embeddings=DeterministicEmbeddings(),
    )

    assert result.answer == INSUFFICIENT_EVIDENCE_MESSAGE
    assert result.sources == ()


def test_query_checks_context_before_creating_embeddings(monkeypatch) -> None:
    from academic_assistant import query

    monkeypatch.setattr(
        query,
        "create_embeddings",
        lambda _: (_ for _ in ()).throw(AssertionError("embedding não deveria ser criado")),
    )

    with pytest.raises(ContextRequiredError, match="instituição"):
        answer_question(
            "Pergunta fictícia",
            RetrievalContext(),
            Settings(),
        )


def test_query_rejects_empty_question_before_external_setup(monkeypatch) -> None:
    from academic_assistant import query

    monkeypatch.setattr(
        query,
        "create_embeddings",
        lambda _: (_ for _ in ()).throw(AssertionError("embedding não deveria ser criado")),
    )

    with pytest.raises(ValueError, match="pergunta"):
        answer_question(
            "  ",
            RetrievalContext(institution="IFMA", course_level="graduação"),
            Settings(),
        )
