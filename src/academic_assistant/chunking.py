"""Divisão de páginas em trechos rastreáveis, sem cruzar páginas."""

from collections.abc import Sequence
from hashlib import sha256

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from academic_assistant.config import Settings


class ChunkingError(ValueError):
    """Uma página não atende ao contrato necessário para a divisão."""


REQUIRED_METADATA = ("document_id", "document_name", "document_hash", "page_number")
SEPARATORS = ["\n\n", "\nArt. ", "\nArtigo ", "\n", ". ", "; ", ", ", " ", ""]


def _validate_page(page: Document) -> None:
    missing = [field for field in REQUIRED_METADATA if field not in page.metadata]
    if missing:
        fields = ", ".join(missing)
        raise ChunkingError(f"Página sem metadados obrigatórios: {fields}.")
    if not page.page_content or not page.page_content.strip():
        raise ChunkingError("Página sem texto não pode ser dividida em trechos.")
    if not isinstance(page.metadata["page_number"], int) or page.metadata["page_number"] < 1:
        raise ChunkingError("page_number deve ser um inteiro começando em 1.")
    for field in ("document_id", "document_name", "document_hash"):
        if not isinstance(page.metadata[field], str) or not page.metadata[field].strip():
            raise ChunkingError(f"{field} deve ser uma string não vazia.")


def _chunk_id(page: Document, position: int, settings: Settings) -> str:
    identity = "\0".join(
        (
            page.metadata["document_id"],
            page.metadata["document_hash"],
            str(page.metadata["page_number"]),
            str(position),
            str(settings.chunk_size),
            str(settings.chunk_overlap),
        )
    )
    return sha256(identity.encode("utf-8")).hexdigest()


def chunk_documents(
    pages: Sequence[Document], settings: Settings | None = None
) -> list[Document]:
    """Divide cada página isoladamente e acrescenta um identificador estável."""
    active_settings = settings or Settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=active_settings.chunk_size,
        chunk_overlap=active_settings.chunk_overlap,
        separators=SEPARATORS,
        keep_separator="start",
        strip_whitespace=False,
    )
    chunks: list[Document] = []
    for page in pages:
        _validate_page(page)
        for position, content in enumerate(splitter.split_text(page.page_content)):
            metadata = dict(page.metadata)
            metadata["chunk_id"] = _chunk_id(page, position, active_settings)
            chunks.append(Document(page_content=content, metadata=metadata))
    return chunks
