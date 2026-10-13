import contextlib
import io
from pathlib import Path
import os
import subprocess
import sys

import pytest
import tempfile
import unittest

from academic_assistant import __version__
from academic_assistant.cli import main
from academic_assistant.config import Settings


class SettingsTests(unittest.TestCase):
    def test_default_settings_do_not_create_directories(self) -> None:
        previous_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            os.chdir(temporary_directory)
            try:
                settings = Settings()

                self.assertEqual(settings.documents_dir, Path("data/documents"))
                self.assertEqual(settings.index_dir, Path("data/index"))
                self.assertEqual(settings.corpus_file, Path("evaluation/corpus.local.json"))
                self.assertEqual(settings.chunk_size, 1_000)
                self.assertEqual(settings.chunk_overlap, 200)
                self.assertEqual(settings.embedding_provider, "nvidia")
                self.assertEqual(settings.embedding_model, "nvidia/nemotron-3-embed-1b")
                self.assertEqual(settings.embedding_dimensions, 2_048)
                self.assertEqual(settings.retrieval_k, 4)
                self.assertEqual(settings.retrieval_page_window, 1)
                self.assertEqual(settings.retrieval_max_chunks, 12)
                self.assertEqual(settings.llm_provider, "nvidia")
                self.assertEqual(
                    settings.llm_model, "nvidia/nemotron-3-super-120b-a12b"
                )
                self.assertEqual(settings.llm_temperature, 1.0)
                self.assertEqual(settings.llm_top_p, 0.95)
                self.assertEqual(settings.llm_max_tokens, 1_024)
                self.assertFalse(Path("data").exists())
            finally:
                os.chdir(previous_directory)

    def test_settings_accept_custom_paths(self) -> None:
        settings = Settings(
            documents_dir=Path("regulations"),
            index_dir=Path("local-index"),
        )

        self.assertEqual(settings.documents_dir, Path("regulations"))
        self.assertEqual(settings.index_dir, Path("local-index"))

    def test_settings_reject_invalid_chunk_limits(self) -> None:
        for values in (
            {"chunk_size": 0},
            {"chunk_overlap": -1},
            {"chunk_size": 100, "chunk_overlap": 100},
            {"chunk_size": 100, "chunk_overlap": 101},
            {"embedding_dimensions": 0},
            {"embedding_model": ""},
            {"embedding_provider": " "},
            {"collection_name": ""},
            {"retrieval_k": 0},
            {"retrieval_page_window": -1},
            {"retrieval_k": 5, "retrieval_max_chunks": 4},
            {"llm_temperature": -0.1},
            {"llm_temperature": 2.1},
            {"llm_top_p": -0.1},
            {"llm_top_p": 1.1},
            {"llm_max_tokens": 0},
            {"llm_provider": ""},
            {"llm_model": " "},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Settings(**values)


class CliTests(unittest.TestCase):
    def test_cli_help(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                main(["--help"])

        self.assertEqual(result.exception.code, 0)
        self.assertIn("Assistente de consulta", output.getvalue())

    def test_cli_version(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaises(SystemExit) as result:
                main(["--version"])

        self.assertEqual(result.exception.code, 0)
        self.assertIn(__version__, output.getvalue())

    def test_cli_rejects_unknown_argument(self) -> None:
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            with self.assertRaises(SystemExit) as result:
                main(["--unknown"])

        self.assertNotEqual(result.exception.code, 0)
        self.assertIn("usage:", error.getvalue())


def test_legacy_cli_imports() -> None:
    from academic_assistant.__main__ import build_parser as legacy_parser, main as legacy_main
    from academic_assistant.cli import build_parser

    assert legacy_main is main
    assert legacy_parser is build_parser


@pytest.mark.parametrize(
    ("arguments", "expected_code", "expected_output"),
    [
        ([], 0, ""),
        (["--help"], 0, "Assistente de consulta"),
        (["--version"], 0, __version__),
        (["--unknown"], 2, "usage:"),
    ],
)
def test_package_entry_point(tmp_path, arguments, expected_code, expected_output) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "academic_assistant", *arguments],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == expected_code
    assert expected_output in result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []
