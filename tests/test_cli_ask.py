"""A interface é testada com respostas e falhas inteiramente fictícias."""

from pathlib import Path

import pytest

from academic_assistant.cli import main
from academic_assistant.indexing import IndexingError
from academic_assistant.retrieval import ContextNotCoveredError, ContextRequiredError
from academic_assistant.validation import (
    INSUFFICIENT_EVIDENCE_MESSAGE,
    AnswerResult,
    AnswerSource,
    AnswerStatus,
)


def supported_result() -> AnswerResult:
    return AnswerResult(
        answer="A regra fictícia permite o pedido. [1]",
        sources=(
            AnswerSource(
                source_id="1",
                document_id="regra.pdf",
                document_name="Regulamento fictício.pdf",
                page_number=4,
                chunk_id="chunk-4",
                excerpt="A regra fictícia permite o pedido.",
            ),
        ),
        status=AnswerStatus.SUPPORTED,
    )


def test_ask_cli_prints_answer_and_verifiable_sources(tmp_path: Path, monkeypatch, capsys) -> None:
    from academic_assistant import query

    captured = {}

    def fake_answer(question, context, settings):
        captured.update(question=question, context=context, settings=settings)
        return supported_result()

    monkeypatch.setattr(query, "answer_question", fake_answer)
    code = main(
        [
            "ask",
            "Posso fazer um pedido fictício?",
            "--institution", "IFMA",
            "--course-level", "graduação",
            "--campus", "Campus Norte",
            "--documents-dir", str(tmp_path / "docs"),
            "--index-dir", str(tmp_path / "index"),
            "--corpus-file", str(tmp_path / "corpus.json"),
        ]
    )
    output = capsys.readouterr()

    assert code == 0
    assert output.err == ""
    assert "Resposta: A regra fictícia permite o pedido. [1]" in output.out
    assert "Fonte [1]" in output.out
    assert "Documento: Regulamento fictício.pdf" in output.out
    assert "Página do PDF: 4" in output.out
    assert 'Trecho: "A regra fictícia permite o pedido."' in output.out
    assert captured["question"] == "Posso fazer um pedido fictício?"
    assert captured["context"].campus == "Campus Norte"
    assert captured["settings"].index_dir == tmp_path / "index"


def test_ask_cli_treats_abstention_as_completed_query(monkeypatch, capsys) -> None:
    from academic_assistant import query

    monkeypatch.setattr(
        query,
        "answer_question",
        lambda *args: AnswerResult(
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            sources=(),
            status=AnswerStatus.INSUFFICIENT_EVIDENCE,
        ),
    )

    code = main(
        ["ask", "Pergunta sem suporte", "--institution", "IFMA", "--course-level", "graduação"]
    )
    output = capsys.readouterr()

    assert code == 0
    assert output.out == f"Resposta: {INSUFFICIENT_EVIDENCE_MESSAGE}\n"
    assert output.err == ""


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (ContextRequiredError("Informe instituição."), "Contexto inválido"),
        (ContextNotCoveredError("Corpus não cobre o contexto."), "Contexto inválido"),
    ],
)
def test_ask_cli_reports_context_problem_with_exit_2(error, message, monkeypatch, capsys) -> None:
    from academic_assistant import query

    monkeypatch.setattr(query, "answer_question", lambda *args: (_ for _ in ()).throw(error))

    code = main(["ask", "Pergunta fictícia"])
    output = capsys.readouterr()

    assert code == 2
    assert output.out == ""
    assert message in output.err


def test_ask_cli_reports_technical_error_on_stderr(monkeypatch, capsys) -> None:
    from academic_assistant import query

    monkeypatch.setattr(
        query,
        "answer_question",
        lambda *args: (_ for _ in ()).throw(IndexingError("Índice fictício ausente.")),
    )

    code = main(
        ["ask", "Pergunta fictícia", "--institution", "IFMA", "--course-level", "graduação"]
    )
    output = capsys.readouterr()

    assert code == 1
    assert output.out == ""
    assert output.err == "Erro de consulta: Índice fictício ausente.\n"


def test_ask_defaults_to_ifma_and_missing_level_does_not_request_institution(capsys):
    from academic_assistant.cli import build_parser
    assert build_parser().parse_args(["ask", "Pergunta"]).institution == "IFMA"
    assert main(["ask", "Posso trancar meu curso?"]) == 2
    error = capsys.readouterr().err
    assert "nível do curso" in error
    assert "instituição" not in error
