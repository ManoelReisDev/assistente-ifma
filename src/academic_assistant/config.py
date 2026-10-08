"""Configuração local do assistente."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Caminhos usados pelo assistente, sem efeitos no sistema de arquivos."""

    documents_dir: Path = Path("data/documents")
    index_dir: Path = Path("data/index")

