"""PDFs sintéticos: todos os textos e regras destes testes são fictícios."""

from hashlib import sha256
from pathlib import Path
import subprocess
import sys

import pytest
from pypdf import PageObject, PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from academic_assistant.cli import main
from academic_assistant.ingestion import IngestionError, ingest_documents


def write_pdf(path: Path, texts: list[str | None], *, protected: bool = False) -> None:
    """Monta PDFs reais com texto simples, sem depender de outro gerador de PDF."""
    writer = PdfWriter()
    for text in texts:
        page = writer.add_blank_page(width=595, height=842)
        if text is not None:
            font = DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
            page[NameObject("/Resources")] = DictionaryObject({
                NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})
            })
            escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET".encode("ascii"))
            page[NameObject("/Contents")] = stream
    if protected:
        writer.encrypt("senha-ficticia")
    writer.write(path)


def test_pages_metadata_and_original_bytes(tmp_path: Path) -> None:
    path = tmp_path / "regra.pdf"
    write_pdf(path, ["Regra ficticia: nao exigir 99 dias.", "Excecao ficticia: apenas no curso X."])
    original = path.read_bytes()

    result = ingest_documents(tmp_path)

    assert len(result.pages) == 2
    assert result.reports[0].status == "complete"
    assert result.reports[0].total_pages == 2
    assert result.reports[0].processed_pages == [1, 2]
    for number, document in enumerate(result.pages, start=1):
        assert document.metadata == {
            "document_id": "regra.pdf", "document_name": "regra.pdf",
            "document_hash": sha256(original).hexdigest(), "page_number": number,
        }
        assert document.page_content == PdfReader(path).pages[number - 1].extract_text()
    assert "nao exigir 99 dias" in result.pages[0].page_content
    assert "Excecao ficticia" not in result.pages[0].page_content
    assert path.read_bytes() == original


def test_identity_and_hash_after_change_and_rename(tmp_path: Path) -> None:
    path = tmp_path / "regra.pdf"
    write_pdf(path, ["Documento ficticio: primeira versao."])
    previous = ingest_documents(tmp_path).pages[0].metadata
    write_pdf(path, ["Documento ficticio: segunda versao."])
    current = ingest_documents(tmp_path).pages[0].metadata
    assert previous["document_id"] == current["document_id"]
    assert previous["document_hash"] != current["document_hash"]
    path.rename(tmp_path / "renomeado.pdf")
    renamed = ingest_documents(tmp_path).pages[0].metadata
    assert renamed["document_id"] != current["document_id"]
    assert renamed["document_hash"] == current["document_hash"]


@pytest.mark.parametrize("texts", [[None], []])
def test_no_text_or_no_pages_rejected(tmp_path: Path, texts: list[str | None]) -> None:
    write_pdf(tmp_path / "vazio.pdf", texts)
    result = ingest_documents(tmp_path)
    assert result.pages == []
    assert result.reports[0].status == "rejected"
    assert result.reports[0].problem
    assert result.reports[0].total_pages == len(texts)
    if texts:
        assert result.reports[0].skipped_pages[0].page_number == 1


def test_mixed_batch_and_nonrecursive_order(tmp_path: Path) -> None:
    (tmp_path / "invalido.pdf").write_bytes(b"nao e PDF")
    write_pdf(tmp_path / "PROTEGIDO.PDF", ["Texto ficticio privado."], protected=True)
    write_pdf(tmp_path / "A.PDF", ["Documento ficticio valido."])
    nested = tmp_path / "subpasta"
    nested.mkdir()
    write_pdf(nested / "ignorado.pdf", ["Nao ler subpastas."])
    (tmp_path / "ignorado.txt").write_text("nao ler")
    result = ingest_documents(tmp_path)
    assert [report.document_name for report in result.reports] == [
        "A.PDF", "invalido.pdf", "PROTEGIDO.PDF"
    ]
    assert [report.status for report in result.reports] == ["complete", "rejected", "rejected"]
    assert len(result.pages) == 1
    assert "protegido" in result.reports[-1].problem.lower()


def test_partial_pdf_keeps_physical_page_numbers(tmp_path: Path) -> None:
    write_pdf(tmp_path / "parcial.pdf", ["Regra ficticia A.", None, "Regra ficticia B."])
    result = ingest_documents(tmp_path)
    report = result.reports[0]
    assert report.status == "partial"
    assert report.total_pages == 3
    assert [page.metadata["page_number"] for page in result.pages] == [1, 3]
    assert report.skipped_pages[0].page_number == 2
    assert "sem texto" in report.skipped_pages[0].reason


def test_page_extraction_failure_preserves_other_pages(tmp_path: Path, monkeypatch) -> None:
    write_pdf(tmp_path / "falha.pdf", ["Falha simulada.", "Regra ficticia preservada."])
    extract = PageObject.extract_text
    calls = 0

    def fail_once(page, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise PdfReadError("Falha simulada de leitura")
        return extract(page, *args, **kwargs)

    monkeypatch.setattr(PageObject, "extract_text", fail_once)
    result = ingest_documents(tmp_path)
    assert result.reports[0].status == "partial"
    assert result.reports[0].skipped_pages[0].page_number == 1
    assert result.pages[0].metadata["page_number"] == 2


def test_file_read_failure_keeps_other_files(tmp_path: Path, monkeypatch) -> None:
    write_pdf(tmp_path / "A.pdf", ["Ficticio."])
    write_pdf(tmp_path / "B.pdf", ["Ficticio valido."])
    read = Path.read_bytes

    def denied(path):
        if path.name == "A.pdf":
            raise PermissionError("Falha simulada")
        return read(path)

    monkeypatch.setattr(Path, "read_bytes", denied)
    result = ingest_documents(tmp_path)
    assert result.reports[0].status == "rejected"
    assert result.reports[1].status == "complete"


def test_invalid_or_empty_folders(tmp_path: Path) -> None:
    for root in (tmp_path / "ausente", tmp_path):
        with pytest.raises(IngestionError):
            ingest_documents(root)
    path = tmp_path / "arquivo.txt"
    path.write_text("nao e pasta")
    with pytest.raises(IngestionError):
        ingest_documents(path)


def test_folder_permission_error(tmp_path: Path, monkeypatch) -> None:
    def denied(path):
        raise PermissionError("Falha simulada")

    monkeypatch.setattr(Path, "iterdir", denied)
    with pytest.raises(IngestionError, match="acessar"):
        ingest_documents(tmp_path)


def test_cli_default_custom_partial_and_invalid(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "data" / "documents"
    folder.mkdir(parents=True)
    write_pdf(folder / "completo.pdf", ["Regra ficticia nao imprimir."])
    assert main(["ingest"]) == 0
    output = capsys.readouterr().out
    assert "Páginas aproveitadas: 1" in output
    assert "completo" in output
    assert "Regra ficticia nao imprimir" not in output

    write_pdf(folder / "parcial.pdf", [None, "Ficticio."])
    assert main(["ingest", "--documents-dir", str(folder)]) == 1
    output = capsys.readouterr().out
    assert "parcial" in output and "Página do PDF 1" in output
    (folder / "invalido.pdf").write_bytes(b"invalido")
    assert main(["ingest", "--documents-dir", str(folder)]) == 1
    assert "rejeitado" in capsys.readouterr().out
    assert main(["ingest", "--documents-dir", str(tmp_path / "ausente")]) == 2
    assert "Erro de ingestão" in capsys.readouterr().err


def test_package_ingest_default_and_custom_folder(tmp_path: Path) -> None:
    folder = tmp_path / "data" / "documents"
    folder.mkdir(parents=True)
    (folder / ".gitkeep").touch()

    def run(*arguments: str):
        return subprocess.run(
            [sys.executable, "-m", "academic_assistant", "ingest", *arguments],
            cwd=tmp_path, capture_output=True, text=True, check=False,
        )

    empty = run()
    assert empty.returncode == 2
    assert "Não encontrei arquivos PDF" in empty.stderr
    write_pdf(folder / "padrao.pdf", ["Regra ficticia."])
    complete = run()
    assert complete.returncode == 0
    assert "Arquivos: 1 | Páginas aproveitadas: 1" in complete.stdout
    assert "padrao.pdf: completo" in complete.stdout

    custom = tmp_path / "personalizados"
    custom.mkdir()
    write_pdf(custom / "parcial.pdf", [None, "Regra ficticia."])
    original = (custom / "parcial.pdf").read_bytes()
    partial = run("--documents-dir", "personalizados")
    assert partial.returncode == 1
    assert "parcial.pdf: parcial" in partial.stdout
    assert "Página do PDF 1" in partial.stdout
    assert (custom / "parcial.pdf").read_bytes() == original
    assert not (folder / "parcial.pdf").exists()
