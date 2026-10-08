"""Extração local de PDFs por página, sem alterar os arquivos de origem."""

from dataclasses import dataclass, field
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Literal

from langchain_core.documents import Document
from pypdf import PdfReader
from pypdf.errors import PyPdfError


class IngestionError(ValueError):
    """A pasta de entrada não permite iniciar a ingestão."""


@dataclass
class PageIssue:
    page_number: int
    reason: str


@dataclass
class FileReport:
    document_name: str
    status: Literal["complete", "partial", "rejected"] = "rejected"
    total_pages: int | None = None
    processed_pages: list[int] = field(default_factory=list)
    skipped_pages: list[PageIssue] = field(default_factory=list)
    problem: str | None = None


@dataclass
class IngestionResult:
    pages: list[Document]
    reports: list[FileReport]


def _extract_file(path: Path, root: Path) -> tuple[list[Document], FileReport]:
    report = FileReport(document_name=path.name)
    pages: list[Document] = []
    try:
        content = path.read_bytes()
        reader = PdfReader(BytesIO(content))
        if reader.is_encrypted:
            report.problem = "PDF protegido; descriptografia não está disponível."
            return [], report
        report.total_pages = len(reader.pages)
        if not report.total_pages:
            report.problem = "PDF sem páginas."
            return [], report
        metadata = {
            "document_id": path.relative_to(root).as_posix(),
            "document_name": path.name,
            "document_hash": sha256(content).hexdigest(),
        }
        for page_index in range(report.total_pages):
            page_number = page_index + 1
            try:
                text = reader.pages[page_index].extract_text()
            except (PyPdfError, OSError, ValueError, UnicodeError):
                report.skipped_pages.append(
                    PageIssue(page_number, "Falha de leitura ou extração da página.")
                )
                continue
            if not text or not text.strip():
                report.skipped_pages.append(
                    PageIssue(page_number, "Página sem texto extraível; pode exigir OCR.")
                )
                continue
            pages.append(
                Document(page_content=text, metadata={**metadata, "page_number": page_number})
            )
            report.processed_pages.append(page_number)
    except OSError:
        report.problem = "Não foi possível ler o arquivo PDF."
        report.processed_pages.clear()
        return [], report
    except (PyPdfError, ValueError, UnicodeError):
        report.problem = "PDF inválido ou leitura do documento interrompida."
        report.processed_pages.clear()
        return [], report

    if not pages:
        report.problem = "PDF sem texto aproveitável; páginas digitalizadas podem exigir OCR."
    else:
        report.status = "partial" if report.skipped_pages else "complete"
    return pages, report


def ingest_documents(documents_dir: Path) -> IngestionResult:
    """Lê PDFs diretamente da pasta e retorna páginas e relatório de cada arquivo."""
    root = Path(documents_dir)
    try:
        if not root.is_dir():
            raise IngestionError("A pasta de documentos não existe ou não é um diretório.")
        paths = sorted(
            (path for path in root.iterdir() if path.suffix.lower() == ".pdf" and path.is_file()),
            key=lambda path: (path.name.casefold(), path.name),
        )
    except OSError as error:
        raise IngestionError("Não foi possível acessar a pasta de documentos.") from error
    if not paths:
        raise IngestionError("Não encontrei arquivos PDF diretamente na pasta de documentos.")

    result = IngestionResult(pages=[], reports=[])
    for path in paths:
        pages, report = _extract_file(path, root)
        result.pages.extend(pages)
        result.reports.append(report)
    return result
