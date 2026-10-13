"""Construção e carga segura do índice vetorial local versionado."""

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from uuid import uuid4
import warnings

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from academic_assistant.chunking import chunk_documents
from academic_assistant.config import Settings
from academic_assistant.ingestion import IngestionError, ingest_documents


INDEX_FORMAT_VERSION = 1
ACTIVE_FILE = "active.json"
MANIFEST_FILE = "manifest.json"
VERSION_PATTERN = re.compile(r"^[0-9TZ-]+-[a-f0-9]{12}$")


class IndexingError(RuntimeError):
    """A construção ou carga do índice não pode ser concluída com segurança."""


class IncompatibleIndexError(IndexingError):
    """O índice ativo usa uma configuração diferente da aplicação."""


class StaleIndexError(IndexingError):
    """Os documentos atuais não correspondem à versão indexada."""


@dataclass(frozen=True, slots=True)
class IndexBuildResult:
    index_id: str
    document_count: int
    page_count: int
    chunk_count: int


@dataclass(frozen=True, slots=True)
class LoadedIndex:
    store: Chroma
    manifest: dict[str, Any]


def create_embeddings(settings: Settings) -> Embeddings:
    """Cria a única integração de embeddings configurada para o MVP."""
    if settings.embedding_provider != "nvidia":
        raise IndexingError(
            f"Provedor de embeddings não suportado: {settings.embedding_provider}."
        )
    if not os.environ.get("NVIDIA_API_KEY", "").strip():
        raise IndexingError("NVIDIA_API_KEY não configurada para gerar embeddings.")
    from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=re.escape(
                    f"Found {settings.embedding_model} in available_models, "
                    "but type is unknown and inference may fail."
                ),
                category=UserWarning,
            )
            return NVIDIAEmbeddings(
                model=settings.embedding_model,
            )
    except Exception as error:
        raise IndexingError(
            "Não foi possível inicializar o modelo de embeddings NVIDIA."
        ) from error


def _read_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise IndexingError(f"{description} não encontrado: {path}.") from error
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise IndexingError(f"Não foi possível ler {description}: {path}.") from error
    if not isinstance(value, dict):
        raise IndexingError(f"{description} deve conter um objeto JSON.")
    return value


def load_corpus_selection(settings: Settings) -> dict[str, dict[str, Any]]:
    """Carrega e valida os documentos selecionados no inventário do corpus."""
    data = _read_json(settings.corpus_file, "Inventário do corpus")
    if data.get("format_version") != 1:
        raise IndexingError("Versão do inventário do corpus não suportada.")
    documents = data.get("documents")
    selection = data.get("selection")
    if not isinstance(documents, list) or not isinstance(selection, dict):
        raise IndexingError("Inventário do corpus sem documentos ou seleção válidos.")
    included = selection.get("included_document_ids")
    if not isinstance(included, list) or not included:
        raise IndexingError("O corpus não possui documentos selecionados para indexação.")
    if len(included) != len(set(included)) or not all(
        isinstance(item, str) and item for item in included
    ):
        raise IndexingError("A seleção do corpus contém identificadores inválidos ou repetidos.")
    by_id = {
        item.get("document_id"): item
        for item in documents
        if isinstance(item, dict) and isinstance(item.get("document_id"), str)
    }
    if any(document_id not in by_id for document_id in included):
        raise IndexingError("A seleção referencia documento ausente do inventário.")
    selected = {document_id: by_id[document_id] for document_id in included}
    if any(item.get("selected") is not True for item in selected.values()):
        raise IndexingError("A seleção e os marcadores dos documentos estão inconsistentes.")
    for document_id, item in selected.items():
        if not isinstance(item.get("document_hash"), str) or not item["document_hash"]:
            raise IndexingError(f"Documento {document_id} sem hash válido no inventário.")
    return selected


def prepare_index_documents(settings: Settings) -> list[Document]:
    """Ingere e divide somente documentos selecionados e integralmente processados."""
    selected = load_corpus_selection(settings)
    try:
        result = ingest_documents(settings.documents_dir)
    except IngestionError as error:
        raise IndexingError(str(error)) from error
    reports = {report.document_name: report for report in result.reports}
    pages_by_document: dict[str, list[Document]] = {}
    for page in result.pages:
        pages_by_document.setdefault(page.metadata["document_id"], []).append(page)

    selected_pages: list[Document] = []
    for document_id, inventory in selected.items():
        report = reports.get(inventory.get("document_name", document_id))
        if report is None:
            raise IndexingError(f"Documento selecionado não encontrado: {document_id}.")
        if report.status != "complete":
            raise IndexingError(
                f"Documento selecionado não foi processado integralmente: {document_id}."
            )
        pages = pages_by_document.get(document_id, [])
        if not pages:
            raise IndexingError(f"Documento selecionado sem páginas: {document_id}.")
        current_hash = pages[0].metadata["document_hash"]
        if current_hash != inventory["document_hash"]:
            raise IndexingError(
                f"Hash divergente para {document_id}; revise o corpus antes de reindexar."
            )
        if any(page.metadata["document_hash"] != current_hash for page in pages):
            raise IndexingError(f"Metadados de versão inconsistentes em {document_id}.")
        selected_pages.extend(pages)
    return chunk_documents(selected_pages, settings)


def _chunk_ids_checksum(chunk_ids: list[str]) -> str:
    return sha256("\n".join(sorted(chunk_ids)).encode("ascii")).hexdigest()


def _document_summaries(chunks: list[Document]) -> list[dict[str, Any]]:
    summaries: dict[str, dict[str, Any]] = {}
    for chunk in chunks:
        document_id = chunk.metadata["document_id"]
        summary = summaries.setdefault(
            document_id,
            {
                "document_id": document_id,
                "document_name": chunk.metadata["document_name"],
                "document_hash": chunk.metadata["document_hash"],
                "pages": set(),
                "chunk_count": 0,
            },
        )
        if summary["document_hash"] != chunk.metadata["document_hash"]:
            raise IndexingError(f"Mais de uma versão recebida para {document_id}.")
        summary["pages"].add(chunk.metadata["page_number"])
        summary["chunk_count"] += 1
    return [
        {
            **{key: value for key, value in summary.items() if key != "pages"},
            "page_count": len(summary["pages"]),
        }
        for _, summary in sorted(summaries.items())
    ]


def _chroma_settings() -> ChromaSettings:
    return ChromaSettings(anonymized_telemetry=False)


def _validate_store(
    store: Chroma, chunk_ids: list[str], embedding_dimensions: int
) -> None:
    stored_ids = store.get(include=[])["ids"]
    if len(stored_ids) != len(chunk_ids) or _chunk_ids_checksum(stored_ids) != _chunk_ids_checksum(chunk_ids):
        raise IndexingError("Os identificadores persistidos no Chroma não correspondem aos trechos.")
    sample = store.get(ids=[chunk_ids[0]], include=["embeddings"])["embeddings"]
    if sample is None or len(sample) != 1 or len(sample[0]) != embedding_dimensions:
        raise IndexingError("A dimensão persistida não corresponde à configuração de embeddings.")


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
        raise IndexingError(f"Não foi possível gravar o arquivo do índice: {path}.") from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def rebuild_index(
    chunks: list[Document], embeddings: Embeddings, settings: Settings
) -> IndexBuildResult:
    """Constrói uma versão completa e só então publica a referência ativa."""
    if not chunks:
        raise IndexingError("Não há trechos para indexar.")
    chunk_ids = [chunk.metadata.get("chunk_id") for chunk in chunks]
    if not all(isinstance(chunk_id, str) and chunk_id for chunk_id in chunk_ids):
        raise IndexingError("Todos os trechos precisam de chunk_id válido.")
    typed_chunk_ids = [str(chunk_id) for chunk_id in chunk_ids]
    if len(typed_chunk_ids) != len(set(typed_chunk_ids)):
        raise IndexingError("A reconstrução contém chunk_id duplicado.")

    index_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:12]}"
    version_dir = settings.index_dir / "versions" / index_id
    chroma_dir = version_dir / "chroma"
    try:
        version_dir.mkdir(parents=True, exist_ok=False)
        store = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            ids=typed_chunk_ids,
            collection_name=settings.collection_name,
            persist_directory=str(chroma_dir),
            client_settings=_chroma_settings(),
        )
        _validate_store(store, typed_chunk_ids, settings.embedding_dimensions)
    except Exception as error:
        if isinstance(error, IndexingError):
            raise
        raise IndexingError(
            "Falha ao gerar embeddings ou persistir a nova versão do índice."
        ) from error
    documents = _document_summaries(chunks)
    manifest = {
        "format_version": INDEX_FORMAT_VERSION,
        "index_id": index_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "collection_name": settings.collection_name,
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
        },
        "chunking": {
            "unit": "characters",
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
        },
        "documents": documents,
        "document_count": len(documents),
        "page_count": sum(item["page_count"] for item in documents),
        "chunk_count": len(chunks),
        "chunk_ids_checksum": _chunk_ids_checksum(typed_chunk_ids),
    }
    _write_json_atomic(version_dir / MANIFEST_FILE, manifest)
    loaded_manifest = _read_json(version_dir / MANIFEST_FILE, "Manifesto do índice")
    if loaded_manifest != manifest:
        raise IndexingError("O manifesto persistido não corresponde à reconstrução.")
    _write_json_atomic(
        settings.index_dir / ACTIVE_FILE,
        {"format_version": INDEX_FORMAT_VERSION, "index_id": index_id},
    )
    return IndexBuildResult(
        index_id=index_id,
        document_count=manifest["document_count"],
        page_count=manifest["page_count"],
        chunk_count=manifest["chunk_count"],
    )


def build_index(settings: Settings, embeddings: Embeddings) -> IndexBuildResult:
    """Prepara o corpus selecionado e publica uma reconstrução completa."""
    return rebuild_index(prepare_index_documents(settings), embeddings, settings)


def _active_manifest(settings: Settings) -> tuple[Path, dict[str, Any]]:
    active = _read_json(settings.index_dir / ACTIVE_FILE, "Referência do índice ativo")
    if active.get("format_version") != INDEX_FORMAT_VERSION:
        raise IncompatibleIndexError("Versão da referência ativa não suportada; reindexe.")
    index_id = active.get("index_id")
    if not isinstance(index_id, str) or not VERSION_PATTERN.fullmatch(index_id):
        raise IndexingError("Referência do índice ativo contém identificador inválido.")
    version_dir = settings.index_dir / "versions" / index_id
    manifest = _read_json(version_dir / MANIFEST_FILE, "Manifesto do índice ativo")
    if manifest.get("index_id") != index_id:
        raise IndexingError("Manifesto e referência ativa não correspondem.")
    return version_dir, manifest


def _validate_manifest_configuration(manifest: dict[str, Any], settings: Settings) -> None:
    expected = {
        "format_version": INDEX_FORMAT_VERSION,
        "collection_name": settings.collection_name,
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "dimensions": settings.embedding_dimensions,
        },
        "chunking": {
            "unit": "characters",
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
        },
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise IncompatibleIndexError(
                f"Configuração incompatível no campo {key}; reconstrua o índice."
            )


def _validate_manifest_totals(manifest: dict[str, Any]) -> None:
    documents = manifest.get("documents")
    if not isinstance(documents, list) or not documents:
        raise IndexingError("Manifesto sem documentos válidos.")
    try:
        document_count = manifest["document_count"]
        page_count = manifest["page_count"]
        chunk_count = manifest["chunk_count"]
        if document_count != len(documents):
            raise ValueError
        if page_count != sum(item["page_count"] for item in documents):
            raise ValueError
        if chunk_count != sum(item["chunk_count"] for item in documents):
            raise ValueError
        if min(document_count, page_count, chunk_count) < 1:
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise IndexingError("Manifesto do índice contém totais inconsistentes.") from error


def _safe_document_path(root: Path, document_id: str) -> Path:
    relative = Path(document_id)
    if relative.is_absolute() or ".." in relative.parts:
        raise StaleIndexError("Manifesto contém caminho de documento inseguro.")
    path = root / relative
    try:
        if path.resolve().parent != root.resolve():
            raise StaleIndexError("Manifesto contém documento fora da pasta cadastrada.")
    except OSError as error:
        raise StaleIndexError("Não foi possível conferir a origem dos documentos.") from error
    return path


def validate_index_sources(manifest: dict[str, Any], settings: Settings) -> None:
    """Confere seleção e hashes atuais sem recalcular embeddings."""
    selected = load_corpus_selection(settings)
    manifest_documents = manifest.get("documents")
    if not isinstance(manifest_documents, list):
        raise IndexingError("Manifesto sem lista válida de documentos.")
    by_id = {
        item.get("document_id"): item
        for item in manifest_documents
        if isinstance(item, dict) and isinstance(item.get("document_id"), str)
    }
    if set(by_id) != set(selected):
        raise StaleIndexError("A seleção do corpus mudou; reconstrua o índice.")
    for document_id, indexed in by_id.items():
        expected_hash = indexed.get("document_hash")
        if selected[document_id].get("document_hash") != expected_hash:
            raise StaleIndexError(
                f"O inventário mudou para {document_id}; reconstrua o índice."
            )
        path = _safe_document_path(settings.documents_dir, document_id)
        try:
            current_hash = sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise StaleIndexError(
                f"Documento indexado ausente ou ilegível: {document_id}."
            ) from error
        if current_hash != expected_hash:
            raise StaleIndexError(
                f"Documento alterado desde a indexação: {document_id}; reindexe."
            )


def load_active_index(
    settings: Settings, embeddings: Embeddings, *, verify_sources: bool = True
) -> LoadedIndex:
    """Carrega somente um índice ativo compatível, completo e de origem atual."""
    version_dir, manifest = _active_manifest(settings)
    _validate_manifest_configuration(manifest, settings)
    _validate_manifest_totals(manifest)
    if verify_sources:
        validate_index_sources(manifest, settings)
    chunk_count = manifest.get("chunk_count")
    checksum = manifest.get("chunk_ids_checksum")
    if not isinstance(chunk_count, int) or chunk_count < 1 or not isinstance(checksum, str):
        raise IndexingError("Manifesto do índice contém totais inválidos.")
    try:
        store = Chroma(
            collection_name=settings.collection_name,
            embedding_function=embeddings,
            persist_directory=str(version_dir / "chroma"),
            client_settings=_chroma_settings(),
            create_collection_if_not_exists=False,
        )
        stored_ids = store.get(include=[])["ids"]
    except Exception as error:
        raise IndexingError("Não foi possível abrir o índice Chroma ativo.") from error
    if len(stored_ids) != chunk_count or _chunk_ids_checksum(stored_ids) != checksum:
        raise IndexingError("O índice Chroma ativo não corresponde ao manifesto.")
    _validate_store(store, stored_ids, settings.embedding_dimensions)
    return LoadedIndex(store=store, manifest=manifest)
