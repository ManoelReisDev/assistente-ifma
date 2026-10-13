"""Textos e regras usados nestes testes são inteiramente fictícios."""

from copy import deepcopy

import pytest
from langchain_core.documents import Document

from academic_assistant.chunking import ChunkingError, chunk_documents
from academic_assistant.config import Settings


def page(text: str, *, number: int = 1, document_hash: str = "a" * 64) -> Document:
    return Document(
        page_content=text,
        metadata={
            "document_id": "regulamento-ficticio.pdf",
            "document_name": "regulamento-ficticio.pdf",
            "document_hash": document_hash,
            "page_number": number,
            "scope": "curso fictício",
        },
    )


def test_chunks_stay_on_their_page_and_preserve_metadata() -> None:
    pages = [
        page("Art. 1º Regra fictícia: não exigir 99 dias. " * 5, number=1),
        page("Art. 2º Exceção fictícia somente para o curso X. " * 5, number=2),
    ]
    original_metadata = deepcopy([item.metadata for item in pages])

    chunks = chunk_documents(pages, Settings(chunk_size=90, chunk_overlap=20))

    assert {chunk.metadata["page_number"] for chunk in chunks} == {1, 2}
    assert len({chunk.metadata["chunk_id"] for chunk in chunks}) == len(chunks)
    for chunk in chunks:
        source = pages[chunk.metadata["page_number"] - 1]
        assert chunk.page_content in source.page_content
        assert len(chunk.page_content) <= 90
        assert "chunk_id" in chunk.metadata
        assert "chunk_id" not in source.metadata
        for key, value in source.metadata.items():
            assert chunk.metadata[key] == value
    assert [item.metadata for item in pages] == original_metadata


def test_conditions_negations_and_article_boundaries_survive() -> None:
    text = (
        "Art. 1º A matrícula fictícia é permitida somente no curso X.\n\n"
        "Art. 2º Não será aceita após 30 dias, exceto no caso Y.\n\n"
        "Art. 3º Outra condição fictícia permanece."
    )

    chunks = chunk_documents([page(text)], Settings(chunk_size=80, chunk_overlap=20))

    combined = "".join(chunk.page_content for chunk in chunks)
    assert "somente no curso X" in combined
    assert "Não será aceita após 30 dias" in combined
    assert "exceto no caso Y" in combined
    assert any(chunk.page_content.startswith("\n\nArt. 2º") for chunk in chunks)


def test_chunk_ids_are_deterministic_and_reflect_version_and_configuration() -> None:
    source = page("Regra fictícia com condição e exceção. " * 12)
    settings = Settings(chunk_size=100, chunk_overlap=20)

    first = chunk_documents([source], settings)
    second = chunk_documents([source], settings)
    changed_version = chunk_documents(
        [page(source.page_content, document_hash="b" * 64)], settings
    )
    changed_split = chunk_documents(
        [source], Settings(chunk_size=110, chunk_overlap=20)
    )

    assert [chunk.metadata["chunk_id"] for chunk in first] == [
        chunk.metadata["chunk_id"] for chunk in second
    ]
    assert first[0].metadata["chunk_id"] != changed_version[0].metadata["chunk_id"]
    assert first[0].metadata["chunk_id"] != changed_split[0].metadata["chunk_id"]


def test_empty_input_returns_empty_list() -> None:
    assert chunk_documents([]) == []


@pytest.mark.parametrize(
    "invalid_page, message",
    [
        (Document(page_content="Texto", metadata={}), "metadados obrigatórios"),
        (page("", number=1), "sem texto"),
        (page("   ", number=1), "sem texto"),
        (page("Texto", number=0), "page_number"),
    ],
)
def test_invalid_pages_are_rejected(invalid_page: Document, message: str) -> None:
    with pytest.raises(ChunkingError, match=message):
        chunk_documents([invalid_page])
