"""Geração estruturada de respostas a partir de evidências recuperadas."""

import os
from typing import Any, Protocol

from academic_assistant.config import Settings
from academic_assistant.prompts import build_generation_messages
from academic_assistant.retrieval import RetrievalResult
from academic_assistant.validation import (
    AnswerResult,
    GenerationValidationError,
    ModelDecision,
    insufficient_evidence_result,
    parse_model_decision,
    validate_model_decision,
)


class GenerationError(RuntimeError):
    """Erro técnico durante a preparação ou chamada de geração."""


class GenerationProviderError(GenerationError):
    """O provedor de linguagem não concluiu a chamada."""


class InvokableModel(Protocol):
    def bind(self, **kwargs: Any) -> "InvokableModel": ...

    def invoke(self, input: Any, **kwargs: Any) -> Any: ...


def create_chat_model(settings: Settings) -> InvokableModel:
    """Cria o único modelo de geração configurado para o MVP."""
    if settings.llm_provider != "nvidia":
        raise GenerationError(f"Provedor de LLM não suportado: {settings.llm_provider}.")
    if not os.environ.get("NVIDIA_API_KEY", "").strip():
        raise GenerationError("NVIDIA_API_KEY não configurada para gerar respostas.")
    from langchain_nvidia_ai_endpoints import ChatNVIDIA

    try:
        return ChatNVIDIA(
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            max_completion_tokens=settings.llm_max_tokens,
            model_kwargs={"chat_template_kwargs": {"enable_thinking": False}},
        )
    except Exception as error:
        raise GenerationProviderError(
            "Não foi possível inicializar o modelo de geração NVIDIA."
        ) from error


def _structured_model(model: InvokableModel) -> InvokableModel:
    schema = ModelDecision.model_json_schema()
    return model.bind(
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "academic_answer",
                "schema": schema,
                "strict": True,
            },
        }
    )


def generate_answer(retrieval: RetrievalResult, model: InvokableModel) -> AnswerResult:
    """Executa uma geração, valida e monta as fontes sem aceitar metadados do LLM."""
    if not retrieval.evidences:
        return insufficient_evidence_result()
    messages = build_generation_messages(retrieval)
    try:
        raw = _structured_model(model).invoke(messages)
    except Exception as error:
        raise GenerationProviderError("O provedor não conseguiu gerar a resposta.") from error
    decision = parse_model_decision(raw)
    return validate_model_decision(decision, retrieval)
