"""Os regulamentos e contextos destes testes são inteiramente fictícios."""

from hashlib import sha256
import json
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from academic_assistant.config import Settings
from academic_assistant.indexing import load_active_index, rebuild_index
from academic_assistant.retrieval import (
    ContextNotCoveredError,
    ContextRequiredError,
    RetrievalContext,
    retrieve_evidence,
)


class DeterministicEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions
        self.query_calls = 0

    def _vector(self, text: str) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        return [(digest[index % len(digest)] + 1) / 256 for index in range(self.dimensions)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        self.query_calls += 1
        return self._vector(text)


def make_settings(tmp_path: Path, **changes) -> Settings:
    values = {
        "documents_dir": tmp_path / "documents",
        "index_dir": tmp_path / "index",
        "corpus_file": tmp_path / "corpus.json",
        "embedding_provider": "test",
        "embedding_model": "deterministic-test",
        "embedding_dimensions": 8,
        "collection_name": "retrieval-test",
        "retrieval_k": 1,
        "retrieval_page_window": 1,
        "retrieval_max_chunks": 4,
        **changes,
    }
    return Settings(**values)


def prepare_index(tmp_path: Path):
    settings = make_settings(tmp_path)
    settings.documents_dir.mkdir()
    definitions = [
        ("geral.pdf", None, ["Introdução fictícia.", "Regra geral fictícia.", "Exceção geral fictícia."]),
        ("campus.pdf", "Campus Norte", ["Procedimento exclusivo fictício do Campus Norte."]),
    ]
    inventory = []
    chunks = []
    for document_id, campus, texts in definitions:
        content = f"arquivo fictício {document_id}".encode()
        (settings.documents_dir / document_id).write_bytes(content)
        document_hash = sha256(content).hexdigest()
        item = {
            "document_id": document_id,
            "document_name": document_id,
            "document_hash": document_hash,
            "institution_id": "IFMA",
            "course_level": "graduação",
            "selected": True,
            "applicability_limits": f"Limitação fictícia de {document_id}.",
        }
        if campus is not None:
            item["campus"] = campus
        inventory.append(item)
        for position, text in enumerate(texts, start=1):
            chunks.append(
                Document(
                    page_content=text,
                    metadata={
                        "document_id": document_id,
                        "document_name": document_id,
                        "document_hash": document_hash,
                        "page_number": position,
                        "chunk_id": sha256(f"{document_id}:{position}".encode()).hexdigest(),
                    },
                )
            )
    settings.corpus_file.write_text(
        json.dumps(
            {
                "format_version": 1,
                "documents": inventory,
                "selection": {
                    "included_document_ids": [item["document_id"] for item in inventory]
                },
            }
        ),
        encoding="utf-8",
    )
    rebuild_index(chunks, DeterministicEmbeddings(), settings)
    query_embeddings = DeterministicEmbeddings()
    return settings, load_active_index(settings, query_embeddings), query_embeddings


def test_retrieval_assigns_sources_and_adds_neighbor_pages(tmp_path: Path) -> None:
    settings, loaded, _ = prepare_index(tmp_path)

    result = retrieve_evidence(
        "Regra geral fictícia.",
        loaded,
        settings,
        RetrievalContext(institution="IFMA", course_level="graduação"),
    )

    assert [item.source_id for item in result.evidences] == ["1", "2", "3"]
    assert result.evidences[0].excerpt == "Regra geral fictícia."
    assert result.evidences[0].is_primary is True
    assert result.evidences[0].distance == pytest.approx(0.0)
    assert {item.page_number for item in result.evidences} == {1, 2, 3}
    assert all(item.document_id == "geral.pdf" for item in result.evidences)
    assert all(item.distance is None for item in result.evidences[1:])
    assert result.source_map["1"].chunk_id == result.evidences[0].chunk_id
    assert result.limitations == ("geral.pdf: Limitação fictícia de geral.pdf.",)


def test_retrieval_filters_campus_specific_document(tmp_path: Path) -> None:
    settings, loaded, _ = prepare_index(tmp_path)

    other_campus = retrieve_evidence(
        "Procedimento exclusivo fictício do Campus Norte.",
        loaded,
        settings,
        RetrievalContext(
            institution="Instituto Federal do Maranhão",
            course_level="graduacao",
            campus="Campus Sul",
        ),
    )
    north_campus = retrieve_evidence(
        "Procedimento exclusivo fictício do Campus Norte.",
        loaded,
        settings,
        RetrievalContext(
            institution="IFMA",
            course_level="graduação",
            campus="Campus Norte",
        ),
    )

    assert {item.document_id for item in other_campus.evidences} == {"geral.pdf"}
    assert north_campus.evidences[0].document_id == "campus.pdf"


def test_missing_or_uncovered_context_stops_before_vector_search(tmp_path: Path) -> None:
    settings, loaded, embeddings = prepare_index(tmp_path)
    calls_before = embeddings.query_calls

    with pytest.raises(ContextRequiredError, match="nível do curso"):
        retrieve_evidence("Pergunta fictícia", loaded, settings, RetrievalContext())
    with pytest.raises(ContextNotCoveredError, match="exclusivamente ao IFMA"):
        retrieve_evidence(
            "Pergunta fictícia",
            loaded,
            settings,
            RetrievalContext(institution="Outra instituição", course_level="graduação"),
        )

    assert embeddings.query_calls == calls_before


def test_retrieval_without_neighbors_respects_top_k(tmp_path: Path) -> None:
    settings, loaded, _ = prepare_index(tmp_path)
    settings = make_settings(
        tmp_path,
        retrieval_k=2,
        retrieval_page_window=0,
        retrieval_max_chunks=2,
    )

    result = retrieve_evidence(
        "Regra geral fictícia.",
        loaded,
        settings,
        RetrievalContext(institution="IFMA", course_level="graduação"),
    )

    assert len(result.evidences) == 2
    assert all(item.is_primary for item in result.evidences)


@pytest.mark.parametrize("institution", [None, "", "IFMA"])
def test_retrieval_assumes_ifma_and_preserves_other_scope_filters(tmp_path, institution):
    settings, loaded, _ = prepare_index(tmp_path)
    result = retrieve_evidence("Regra geral fictícia.", loaded, settings,
                               RetrievalContext(institution=institution, course_level="graduação"))
    assert result.context.institution == "IFMA"
    assert {item.document_id for item in result.evidences} == {"geral.pdf"}


def test_precedence_metadata_comes_from_inventory_without_reindexing(tmp_path):
    settings, loaded, _ = prepare_index(tmp_path)
    corpus = json.loads(settings.corpus_file.read_text())
    corpus["documents"][0].update(publication_date="2025-01-01", precedence_group="norma-geral")
    settings.corpus_file.write_text(json.dumps(corpus))
    result = retrieve_evidence("Regra geral fictícia.", loaded, settings,
                               RetrievalContext(course_level="graduação"))
    assert all(e.publication_date == "2025-01-01" for e in result.evidences)
    assert all(e.precedence_group == "norma-geral" for e in result.evidences)


def test_precedence_group_cannot_replace_general_rule_with_campus_rule(tmp_path):
    settings, loaded, embeddings = prepare_index(tmp_path)
    corpus = json.loads(settings.corpus_file.read_text())
    for item in corpus["documents"]:
        item.update(publication_date="2025-01-01", precedence_group="grupo-incoerente")
    settings.corpus_file.write_text(json.dumps(corpus))
    from academic_assistant.retrieval import RetrievalError
    before = embeddings.query_calls
    with pytest.raises(RetrievalError, match="mistura escopos"):
        retrieve_evidence("Pergunta", loaded, settings,
                          RetrievalContext(course_level="graduação", campus="Campus Norte"))
    assert embeddings.query_calls == before


def test_latest_version_is_filtered_before_search_even_when_old_text_matches_better(tmp_path):
    settings, loaded, _ = prepare_index(tmp_path)
    corpus = json.loads(settings.corpus_file.read_text())
    old, new = corpus["documents"]
    new.pop("campus", None)
    old.update(publication_date="2020-01-01", precedence_group="mesmo-escopo")
    new.update(publication_date="2025-01-01", precedence_group="mesmo-escopo")
    settings.corpus_file.write_text(json.dumps(corpus))
    result = retrieve_evidence("Regra geral fictícia.", loaded, settings,
                               RetrievalContext(course_level="graduação"))
    assert {item.document_id for item in result.evidences} == {"campus.pdf"}
    assert any("Fonte priorizada: campus.pdf (2025-01-01)" in value for value in result.limitations)
    assert not any(value.startswith("geral.pdf:") for value in result.limitations)
