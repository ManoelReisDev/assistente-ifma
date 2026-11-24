"""Referências locais da documentação de entrada, sem acesso ao corpus."""

from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("relative_path", [
    "README.md", "reports/RELATORIO-GERAL.md",
    "reports/RELATORIO-PROGRESSO.md", "reports/PLANO-EXECUCAO.md",
])
def test_local_markdown_links_exist(relative_path):
    document = ROOT / relative_path
    missing = []
    for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
        for target in re.findall(r"\]\(([^)]+)\)", line):
            if "://" in target or target.startswith("#"):
                continue
            if not (document.parent / target.split("#")[0]).exists():
                missing.append(f"{relative_path}:{line_number}: {target}")

    assert not missing, "\n".join(missing)
