"""Configuração local do assistente."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    """Configurações locais do assistente, sem efeitos no sistema de arquivos."""

    documents_dir: Path = Path("data/documents")
    index_dir: Path = Path("data/index")
    corpus_file: Path = Path("evaluation/corpus.local.json")
    chunk_size: int = 1_000
    chunk_overlap: int = 200
    embedding_provider: str = "nvidia"
    embedding_model: str = "nvidia/nemotron-3-embed-1b"
    embedding_dimensions: int = 2_048
    collection_name: str = "academic-regulations"
    retrieval_k: int = 4
    retrieval_page_window: int = 1
    retrieval_max_chunks: int = 12
    llm_provider: str = "nvidia"
    llm_model: str = "nvidia/nemotron-3-super-120b-a12b"
    llm_temperature: float = 0.0
    llm_top_p: float = 0.95
    llm_max_tokens: int = 1_024

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size deve ser maior que zero.")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap não pode ser negativo.")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap deve ser menor que chunk_size.")
        if self.embedding_dimensions <= 0:
            raise ValueError("embedding_dimensions deve ser maior que zero.")
        if self.retrieval_k <= 0:
            raise ValueError("retrieval_k deve ser maior que zero.")
        if self.retrieval_page_window < 0:
            raise ValueError("retrieval_page_window não pode ser negativo.")
        if self.retrieval_max_chunks < self.retrieval_k:
            raise ValueError("retrieval_max_chunks deve ser maior ou igual a retrieval_k.")
        if not 0 <= self.llm_temperature <= 2:
            raise ValueError("llm_temperature deve estar entre 0 e 2.")
        if not 0 <= self.llm_top_p <= 1:
            raise ValueError("llm_top_p deve estar entre 0 e 1.")
        if self.llm_max_tokens <= 0:
            raise ValueError("llm_max_tokens deve ser maior que zero.")
        for field in (
            "embedding_provider",
            "embedding_model",
            "collection_name",
            "llm_provider",
            "llm_model",
        ):
            if not getattr(self, field).strip():
                raise ValueError(f"{field} deve ser uma string não vazia.")

