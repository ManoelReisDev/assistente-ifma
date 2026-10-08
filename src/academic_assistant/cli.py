"""Interface de linha de comando do assistente."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from academic_assistant import __version__
from academic_assistant.config import Settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m academic_assistant",
        description="Assistente de consulta a regulamentos acadêmicos.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command")
    ingest = commands.add_parser("ingest", help="Extrair PDFs locais por página.")
    ingest.add_argument(
        "--documents-dir", type=Path, default=Settings().documents_dir,
        help="Pasta de PDFs (padrão: data/documents).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ingest":
        from academic_assistant.ingestion import IngestionError, ingest_documents

        try:
            result = ingest_documents(args.documents_dir)
        except IngestionError as error:
            print(f"Erro de ingestão: {error}", file=sys.stderr)
            return 2
        labels = {"complete": "completo", "partial": "parcial", "rejected": "rejeitado"}
        print(f"Arquivos: {len(result.reports)} | Páginas aproveitadas: {len(result.pages)}")
        for report in result.reports:
            total = report.total_pages if report.total_pages is not None else "desconhecido"
            print(
                f"{report.document_name}: {labels[report.status]} | "
                f"Páginas: {len(report.processed_pages)}/{total}"
            )
            if report.problem:
                print(f"  Problema: {report.problem}")
            for issue in report.skipped_pages:
                print(f"  Página do PDF {issue.page_number}: {issue.reason}")
        return int(any(report.status != "complete" for report in result.reports))
    return 0
