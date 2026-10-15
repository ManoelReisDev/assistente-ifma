"""Contrato e validação determinística da resposta gerada."""

from dataclasses import dataclass
from enum import Enum
import json
import re
from typing import Any

from langchain_core.messages import AIMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from academic_assistant.retrieval import RetrievalResult


INSUFFICIENT_EVIDENCE_MESSAGE = (
    "Não encontrei evidências suficientes nos documentos cadastrados para responder a essa pergunta."
)
CITATION_PATTERN = re.compile(r"\[([^\[\]\n]+)\]")


class GenerationValidationError(RuntimeError):
    """A saída do modelo viola o contrato e não pode ser exibida."""


class AnswerStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIAL = "partial"
    CONFLICT = "conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ModelDecision(BaseModel):
    """Únicos dados que o modelo pode escolher para compor a resposta."""

    model_config = ConfigDict(extra="forbid")

    status: AnswerStatus
    answer: str = Field(
        description=(
            "Resposta em português sem referências entre colchetes; a aplicação "
            "acrescentará as citações após validar source_ids."
        ),
        examples=["A regra fictícia permite a solicitação."],
    )
    source_ids: list[str] = Field(
        description=(
            "Identificadores fornecidos que sustentam a resposta, sem metadados adicionais."
        )
    )
    unsupported_parts: list[str] = Field(
        description=(
            "Somente para status partial: partes da pergunta que não puderam ser "
            "respondidas pelas evidências. Deve ser vazia nos demais estados."
        )
    )


@dataclass(frozen=True, slots=True)
class AnswerSource:
    source_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_id: str
    excerpt: str


@dataclass(frozen=True, slots=True)
class AnswerResult:
    answer: str
    sources: tuple[AnswerSource, ...]
    status: AnswerStatus


def parse_model_decision(raw: Any) -> ModelDecision:
    """Converte somente formatos explícitos; conteúdo inesperado é rejeitado."""
    try:
        if isinstance(raw, ModelDecision):
            return raw
        if isinstance(raw, AIMessage):
            raw = raw.content
        if isinstance(raw, str):
            return ModelDecision.model_validate_json(raw)
        if isinstance(raw, dict):
            return ModelDecision.model_validate(raw)
    except (ValidationError, json.JSONDecodeError) as error:
        raise GenerationValidationError("O modelo retornou uma estrutura inválida.") from error
    raise GenerationValidationError("O modelo retornou um tipo de saída inválido.")


def _sources_for_ids(
    source_ids: list[str], retrieval: RetrievalResult
) -> tuple[AnswerSource, ...]:
    if len(source_ids) != len(set(source_ids)):
        raise GenerationValidationError("A resposta contém identificadores de fonte repetidos.")
    source_map = retrieval.source_map
    unknown = [source_id for source_id in source_ids if source_id not in source_map]
    if unknown:
        raise GenerationValidationError("A resposta cita uma fonte inexistente.")
    if set(source_ids) & retrieval.superseded_source_ids:
        raise GenerationValidationError("A resposta cita uma versão anterior; use a fonte mais recente do grupo revisado.")
    return tuple(
        AnswerSource(
            source_id=item.source_id,
            document_id=item.document_id,
            document_name=item.document_name,
            page_number=item.page_number,
            chunk_id=item.chunk_id,
            excerpt=item.excerpt,
        )
        for item in (source_map[source_id] for source_id in source_ids)
    )


def validate_model_decision(
    decision: ModelDecision, retrieval: RetrievalResult
) -> AnswerResult:
    """Valida referências e monta fontes exclusivamente a partir da recuperação."""
    answer = decision.answer.strip()
    source_ids = [source_id.strip() for source_id in decision.source_ids]
    unsupported_parts = [part.strip() for part in decision.unsupported_parts]
    if any(not source_id for source_id in source_ids):
        raise GenerationValidationError("A resposta contém source_id vazio.")
    if any(not part for part in unsupported_parts):
        raise GenerationValidationError("A resposta contém parte não sustentada vazia.")
    if len(unsupported_parts) != len(set(unsupported_parts)):
        raise GenerationValidationError("A resposta repete partes não sustentadas.")
    citations = CITATION_PATTERN.findall(answer)

    if decision.status is AnswerStatus.INSUFFICIENT_EVIDENCE:
        if source_ids or citations or unsupported_parts:
            raise GenerationValidationError(
                "Resposta sem evidência não pode conter referências."
            )
        return AnswerResult(
            answer=INSUFFICIENT_EVIDENCE_MESSAGE,
            sources=(),
            status=decision.status,
        )

    if not answer:
        raise GenerationValidationError("A resposta gerada está vazia.")
    if not source_ids:
        raise GenerationValidationError("Uma resposta acadêmica precisa citar fontes.")
    if citations:
        raise GenerationValidationError(
            "O modelo não deve produzir referências; elas são montadas pela aplicação."
        )
    if decision.status is AnswerStatus.PARTIAL and not unsupported_parts:
        raise GenerationValidationError(
            "Uma resposta parcial deve identificar a parte não sustentada."
        )
    if decision.status is not AnswerStatus.PARTIAL and unsupported_parts:
        raise GenerationValidationError(
            "Somente uma resposta parcial pode declarar partes não sustentadas."
        )
    sources = _sources_for_ids(source_ids, retrieval)
    if decision.status is AnswerStatus.CONFLICT and len(sources) < 2:
        raise GenerationValidationError("Um conflito precisa de ao menos duas fontes.")

    answer += " " + " ".join(f"[{source_id}]" for source_id in source_ids)
    if unsupported_parts:
        answer += "\n\nNão encontrei evidências suficientes para: " + "; ".join(
            unsupported_parts
        ) + "."
    if retrieval.limitations:
        answer += "\n\nLimitação do corpus: " + " ".join(retrieval.limitations)
    superseded = retrieval.superseded_source_ids
    if superseded:
        preferred = {
            source.precedence_group: source
            for source_id in source_ids
            if (source := retrieval.source_map[source_id]).precedence_group
            and any(retrieval.source_map[old].precedence_group == source.precedence_group for old in superseded)
        }
        if preferred:
            answer += "\n\n" + " ".join(
                f"Fonte priorizada: {source.document_name} ({source.publication_date}), "
                f"por ser a versão mais recente do grupo revisado [{source.source_id}]."
                for source in preferred.values()
            )
    return AnswerResult(answer=answer, sources=sources, status=decision.status)


def insufficient_evidence_result() -> AnswerResult:
    """Retorna a abstenção obrigatória sem depender do modelo."""
    return AnswerResult(
        answer=INSUFFICIENT_EVIDENCE_MESSAGE,
        sources=(),
        status=AnswerStatus.INSUFFICIENT_EVIDENCE,
    )
