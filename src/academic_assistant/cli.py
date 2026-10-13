"""Interface de linha de comando do assistente."""

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from academic_assistant import __version__
from academic_assistant.config import Settings

if TYPE_CHECKING:
    from academic_assistant.validation import AnswerResult


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
    index = commands.add_parser("index", help="Reconstruir e publicar o índice local.")
    index.add_argument(
        "--documents-dir", type=Path, default=Settings().documents_dir,
        help="Pasta de PDFs (padrão: data/documents).",
    )
    index.add_argument(
        "--index-dir", type=Path, default=Settings().index_dir,
        help="Pasta do índice (padrão: data/index).",
    )
    index.add_argument(
        "--corpus-file", type=Path, default=Settings().corpus_file,
        help="Inventário do corpus (padrão: evaluation/corpus.local.json).",
    )
    ask = commands.add_parser("ask", help="Consultar o índice ativo com fontes.")
    ask.add_argument("question", help="Pergunta em linguagem natural.")
    ask.add_argument("--institution", help="Instituição aplicável, por exemplo IFMA.")
    ask.add_argument("--course-level", help="Nível do curso, por exemplo graduação.")
    ask.add_argument("--campus", help="Campus aplicável, quando informado.")
    ask.add_argument("--modality", help="Modalidade aplicável, quando informada.")
    ask.add_argument(
        "--documents-dir", type=Path, default=Settings().documents_dir,
        help="Pasta de PDFs (padrão: data/documents).",
    )
    ask.add_argument(
        "--index-dir", type=Path, default=Settings().index_dir,
        help="Pasta do índice (padrão: data/index).",
    )
    ask.add_argument(
        "--corpus-file", type=Path, default=Settings().corpus_file,
        help="Inventário do corpus (padrão: evaluation/corpus.local.json).",
    )
    return parser


def _print_answer(result: "AnswerResult") -> None:
    print(f"Resposta: {result.answer}")
    for source in result.sources:
        print()
        print(f"Fonte [{source.source_id}]")
        print(f"Documento: {source.document_name}")
        print(f"Página do PDF: {source.page_number}")
        print(f'Trecho: "{source.excerpt}"')


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
    if args.command == "index":
        from academic_assistant.indexing import (
            IndexingError,
            build_index,
            create_embeddings,
        )

        settings = Settings(
            documents_dir=args.documents_dir,
            index_dir=args.index_dir,
            corpus_file=args.corpus_file,
        )
        try:
            result = build_index(settings, create_embeddings(settings))
        except IndexingError as error:
            print(f"Erro de indexação: {error}", file=sys.stderr)
            return 1
        print(
            f"Índice ativo: {result.index_id} | Documentos: {result.document_count} | "
            f"Páginas: {result.page_count} | Trechos: {result.chunk_count}"
        )
        return 0
    if args.command == "ask":
        from academic_assistant.generation import GenerationError
        from academic_assistant.indexing import IndexingError
        from academic_assistant.query import answer_question
        from academic_assistant.retrieval import (
            ContextNotCoveredError,
            ContextRequiredError,
            RetrievalContext,
            RetrievalError,
        )
        from academic_assistant.validation import GenerationValidationError

        settings = Settings(
            documents_dir=args.documents_dir,
            index_dir=args.index_dir,
            corpus_file=args.corpus_file,
        )
        context = RetrievalContext(
            institution=args.institution,
            course_level=args.course_level,
            campus=args.campus,
            modality=args.modality,
        )
        try:
            result = answer_question(args.question, context, settings)
        except (ContextRequiredError, ContextNotCoveredError, ValueError) as error:
            print(f"Contexto inválido: {error}", file=sys.stderr)
            return 2
        except (
            IndexingError,
            RetrievalError,
            GenerationError,
            GenerationValidationError,
        ) as error:
            print(f"Erro de consulta: {error}", file=sys.stderr)
            return 1
        _print_answer(result)
        return 0
    return 0
