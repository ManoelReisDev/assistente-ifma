"""Entrada do pacote e compatibilidade dos imports da CLI."""

from academic_assistant.cli import build_parser, main

__all__ = ["build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
