"""Índice e conteúdos usados nestes testes são inteiramente fictícios."""

from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import warnings

import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from academic_assistant import indexing
from academic_assistant.config import Settings
from academic_assistant.indexing import (
    IncompatibleIndexError,
    IndexBuildResult,
    IndexingError,
    StaleIndexError,
    load_active_index,
    prepare_index_documents,
    rebuild_index,
)
from academic_assistant.ingestion import FileReport, IngestionResult


class DeterministicEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 8, *, fail: bool = False) -> None:
        self.dimensions = dimensions
        self.fail = fail
        self.document_calls = 0
        self.query_calls = 0

    def _vector(self, text: str) -> list[float]:
        digest = sha256(text.encode("utf-8")).digest()
        return [(digest[index % len(digest)] + 1) / 256 for index in range(self.dimensions)]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls += 1
        if self.fail:
            raise RuntimeError("Falha fictícia de embeddings")
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
        "collection_name": "academic-test",
        **changes,
    }
    return Settings(**values)


def write_sources(settings: Settings, files: dict[str, bytes]) -> dict[str, str]:
    settings.documents_dir.mkdir(parents=True, exist_ok=True)
    documents = []
    hashes = {}
    for document_id, content in files.items():
        (settings.documents_dir / document_id).write_bytes(content)
        document_hash = sha256(content).hexdigest()
        hashes[document_id] = document_hash
        documents.append(
            {
                "document_id": document_id,
                "document_name": document_id,
                "document_hash": document_hash,
                "selected": True,
            }
        )
    settings.corpus_file.write_text(
        json.dumps(
            {
                "format_version": 1,
                "documents": documents,
                "selection": {"included_document_ids": list(files)},
            }
        ),
        encoding="utf-8",
    )
    return hashes


def make_chunks(document_id: str, document_hash: str, texts: list[str]) -> list[Document]:
    return [
        Document(
            page_content=text,
            metadata={
                "document_id": document_id,
                "document_name": document_id,
                "document_hash": document_hash,
                "page_number": position + 1,
                "chunk_id": sha256(f"{document_id}:{position}:{text}".encode()).hexdigest(),
            },
        )
        for position, text in enumerate(texts)
    ]


def test_persistent_index_reloads_without_embedding_documents(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hashes = write_sources(settings, {"regra.pdf": b"pdf ficticio versao 1"})
    chunks = make_chunks(
        "regra.pdf",
        hashes["regra.pdf"],
        ["Regra fictícia sobre matrícula.", "Exceção fictícia do curso X."],
    )
    builder_embeddings = DeterministicEmbeddings()

    result = rebuild_index(chunks, builder_embeddings, settings)
    query_embeddings = DeterministicEmbeddings()
    loaded = load_active_index(settings, query_embeddings)
    stored = loaded.store.get(include=[])["ids"]
    matches = loaded.store.similarity_search("matrícula fictícia", k=1)

    assert result.document_count == 1
    assert result.page_count == 2
    assert result.chunk_count == 2
    assert set(stored) == {chunk.metadata["chunk_id"] for chunk in chunks}
    assert query_embeddings.document_calls == 0
    assert query_embeddings.query_calls == 1
    assert matches[0].metadata["document_id"] == "regra.pdf"
    assert loaded.manifest["embedding"]["model"] == "deterministic-test"


def test_failed_rebuild_preserves_active_version(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hashes = write_sources(settings, {"regra.pdf": b"pdf ficticio"})
    chunks = make_chunks("regra.pdf", hashes["regra.pdf"], ["Regra válida fictícia."])
    first = rebuild_index(chunks, DeterministicEmbeddings(), settings)
    active_before = (settings.index_dir / "active.json").read_bytes()

    with pytest.raises(IndexingError, match="Falha ao gerar embeddings"):
        rebuild_index(chunks, DeterministicEmbeddings(fail=True), settings)

    assert (settings.index_dir / "active.json").read_bytes() == active_before
    loaded = load_active_index(settings, DeterministicEmbeddings())
    assert loaded.manifest["index_id"] == first.index_id


def test_successful_rebuild_replaces_active_contents_without_residue(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    first_hash = write_sources(settings, {"regra.pdf": b"primeira versao"})["regra.pdf"]
    old_chunks = make_chunks("regra.pdf", first_hash, ["Regra antiga fictícia."])
    first = rebuild_index(old_chunks, DeterministicEmbeddings(), settings)

    second_hash = write_sources(settings, {"regra.pdf": b"segunda versao"})["regra.pdf"]
    new_chunks = make_chunks("regra.pdf", second_hash, ["Regra nova fictícia."])
    second = rebuild_index(new_chunks, DeterministicEmbeddings(), settings)
    loaded = load_active_index(settings, DeterministicEmbeddings())

    assert first.index_id != second.index_id
    assert loaded.store.get(include=[])["ids"] == [new_chunks[0].metadata["chunk_id"]]
    assert (settings.index_dir / "versions" / first.index_id / "manifest.json").is_file()
    assert loaded.manifest["documents"][0]["document_hash"] == second_hash


def test_load_rejects_changed_sources_and_incompatible_configuration(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    hashes = write_sources(settings, {"regra.pdf": b"versao indexada"})
    chunks = make_chunks("regra.pdf", hashes["regra.pdf"], ["Regra fictícia."])
    rebuild_index(chunks, DeterministicEmbeddings(), settings)

    incompatible = replace(settings, chunk_size=settings.chunk_size + 1)
    with pytest.raises(IncompatibleIndexError, match="reconstrua"):
        load_active_index(incompatible, DeterministicEmbeddings())

    migrated_provider = replace(
        settings,
        embedding_provider="nvidia",
        embedding_model="nvidia/nemotron-3-embed-1b",
        embedding_dimensions=2_048,
    )
    with pytest.raises(IncompatibleIndexError, match="embedding"):
        load_active_index(migrated_provider, DeterministicEmbeddings(2_048))

    (settings.documents_dir / "regra.pdf").write_bytes(b"versao alterada")
    with pytest.raises(StaleIndexError, match="alterado"):
        load_active_index(settings, DeterministicEmbeddings())


def test_selected_partial_document_blocks_preparation(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    hashes = write_sources(settings, {"regra.pdf": b"pdf parcial"})
    page = Document(
        page_content="Página fictícia aproveitada.",
        metadata={
            "document_id": "regra.pdf",
            "document_name": "regra.pdf",
            "document_hash": hashes["regra.pdf"],
            "page_number": 1,
        },
    )
    monkeypatch.setattr(
        indexing,
        "ingest_documents",
        lambda _: IngestionResult(
            pages=[page],
            reports=[FileReport(document_name="regra.pdf", status="partial")],
        ),
    )

    with pytest.raises(IndexingError, match="integralmente"):
        prepare_index_documents(settings)


def test_create_embeddings_requires_nvidia_key(monkeypatch) -> None:
    for value in (None, " "):
        if value is None:
            monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
        else:
            monkeypatch.setenv("NVIDIA_API_KEY", value)
        with pytest.raises(IndexingError, match="NVIDIA_API_KEY"):
            indexing.create_embeddings(Settings())


def test_create_embeddings_uses_configured_nvidia_model(monkeypatch) -> None:
    captured = {}

    class FakeNVIDIAEmbeddings:
        def __init__(self, **kwargs) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-chave-ficticia")
    monkeypatch.setitem(
        sys.modules,
        "langchain_nvidia_ai_endpoints",
        SimpleNamespace(NVIDIAEmbeddings=FakeNVIDIAEmbeddings),
    )

    result = indexing.create_embeddings(Settings())

    assert isinstance(result, FakeNVIDIAEmbeddings)
    assert captured == {"model": "nvidia/nemotron-3-embed-1b"}


def test_create_embeddings_suppresses_only_known_catalog_warning(monkeypatch) -> None:
    class WarningNVIDIAEmbeddings:
        def __init__(self, **kwargs) -> None:
            warnings.warn(
                f"Found {kwargs['model']} in available_models, "
                "but type is unknown and inference may fail.",
                UserWarning,
            )
            warnings.warn("aviso fictício diferente", UserWarning)

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-chave-ficticia")
    monkeypatch.setitem(
        sys.modules,
        "langchain_nvidia_ai_endpoints",
        SimpleNamespace(NVIDIAEmbeddings=WarningNVIDIAEmbeddings),
    )

    with pytest.warns(UserWarning, match="aviso fictício diferente") as captured:
        indexing.create_embeddings(Settings())

    assert len(captured) == 1


def test_create_embeddings_wraps_provider_initialization_failure(monkeypatch) -> None:
    class FailingNVIDIAEmbeddings:
        def __init__(self, **kwargs) -> None:
            raise RuntimeError("falha fictícia do catálogo")

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-chave-ficticia")
    monkeypatch.setitem(
        sys.modules,
        "langchain_nvidia_ai_endpoints",
        SimpleNamespace(NVIDIAEmbeddings=FailingNVIDIAEmbeddings),
    )

    with pytest.raises(IndexingError, match="inicializar"):
        indexing.create_embeddings(Settings())


def test_index_cli_reports_published_version(tmp_path: Path, monkeypatch, capsys) -> None:
    from academic_assistant.cli import main

    captured = {}

    def fake_embeddings(settings):
        captured["settings"] = settings
        return DeterministicEmbeddings()

    def fake_build(settings, embeddings):
        assert settings is captured["settings"]
        assert isinstance(embeddings, DeterministicEmbeddings)
        return IndexBuildResult("20261013T000000Z-abcdef123456", 2, 7, 15)

    monkeypatch.setattr(indexing, "create_embeddings", fake_embeddings)
    monkeypatch.setattr(indexing, "build_index", fake_build)
    code = main(
        [
            "index",
            "--documents-dir", str(tmp_path / "docs"),
            "--index-dir", str(tmp_path / "idx"),
            "--corpus-file", str(tmp_path / "corpus.json"),
        ]
    )

    assert code == 0
    assert "Documentos: 2 | Páginas: 7 | Trechos: 15" in capsys.readouterr().out
    assert captured["settings"].index_dir == tmp_path / "idx"
