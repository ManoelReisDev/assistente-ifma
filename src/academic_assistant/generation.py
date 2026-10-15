"""Geração estruturada de respostas a partir de evidências recuperadas."""

import os
from typing import Any, Protocol

from langchain_core.messages import AIMessage, HumanMessage

from academic_assistant.config import Settings
from academic_assistant.prompts import build_generation_messages
from academic_assistant.retrieval import RetrievalResult
from academic_assistant.validation import (
    AnswerResult,
    AnswerStatus,
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


def _normalize_abstention(decision: ModelDecision) -> ModelDecision:
    if decision.status is not AnswerStatus.INSUFFICIENT_EVIDENCE:
        return decision
    return ModelDecision(
        status=decision.status,
        answer=decision.answer,
        source_ids=[],
        unsupported_parts=[],
    )


def generate_answer(
    retrieval: RetrievalResult, model: InvokableModel,
    *, trace: list[dict[str, Any]] | None = None,
) -> AnswerResult:
    """Gera, revisa no máximo uma abstenção e monta fontes validadas."""
    if not retrieval.evidences:
        return insufficient_evidence_result()
    def interpret(raw: Any, purpose: str) -> tuple[ModelDecision, AnswerResult | None, str | None]:
        event: dict[str, Any] = {"purpose": purpose, "received": None,
                                 "validation_error": None, "selected": False}
        if trace is not None:
            trace.append(event)
        try:
            received = parse_model_decision(raw)
            event["received"] = received.model_dump(mode="json")
            decision = _normalize_abstention(received)
            event["normalized"] = decision.model_dump(mode="json")
        except GenerationValidationError as error:
            event["validation_error"] = str(error)
            content = raw.content if isinstance(raw, AIMessage) else raw
            if isinstance(content, str):
                event["malformed_output"] = content
            raise
        try:
            result = validate_model_decision(decision, retrieval)
        except GenerationValidationError as error:
            event["validation_error"] = str(error)
            return decision, None, str(error)
        event["validated"] = True
        return decision, result, None

    def select(result: AnswerResult, index: int = -1) -> AnswerResult:
        if trace is not None:
            trace[index]["selected"] = True
        return result

    messages = build_generation_messages(retrieval)
    structured = _structured_model(model)

    def invoke(input: Any, purpose: str) -> Any:
        try:
            return structured.invoke(input)
        except Exception:
            if trace is not None:
                trace.append({"purpose": purpose, "received": None,
                              "provider_error": "Falha na invocação do provedor.",
                              "selected": False})
            raise
    try:
        raw = invoke(messages, "initial")
    except Exception as error:
        raise GenerationProviderError("O provedor não conseguiu gerar a resposta.") from error
    decision, first_result, validation_error = interpret(raw, "initial")
    if first_result is None:
        correction_messages = [
            *messages,
            AIMessage(content=decision.model_dump_json()),
            HumanMessage(
                content=(
                    "Corrija uma única vez a saída estruturada. Erro da validação: "
                    f"{validation_error} Respeite todos os estados, source_ids e "
                    "unsupported_parts definidos no prompt; não acrescente metadados."
                )
            ),
        ]
        try:
            raw = invoke(correction_messages, "correction")
        except Exception as error:
            raise GenerationProviderError(
                "O provedor não conseguiu corrigir a resposta inválida."
            ) from error
        corrected_decision, corrected_result, _ = interpret(raw, "correction")
        if corrected_result is None:
            return validate_model_decision(corrected_decision, retrieval)
        return select(corrected_result)
    if decision.status.value == "insufficient_evidence":
        review_messages = [
            *messages,
            AIMessage(content=decision.model_dump_json()),
            HumanMessage(
                content=(
                    "Revise uma única vez a decisão de falta de evidência. Há trechos "
                    "recuperados: verifique condições cumulativas, respostas negativas "
                    "diretas e partes sustentadas. Use partial se apenas parte puder ser "
                    "respondida. Regras complementares não são conflito. Mantenha "
                    "insufficient_evidence se nenhum trecho sustentar uma resposta. "
                    "Uma resposta negativa documentada é supported, não partial. "
                    "Se não há parte solicitada sem suporte, use supported com "
                    "unsupported_parts vazio; partial exige descrever a parte ausente."
                )
            ),
        ]
        try:
            raw = invoke(review_messages, "abstention_review")
        except Exception as error:
            raise GenerationProviderError(
                "O provedor não conseguiu revisar a resposta."
            ) from error
        revised_decision, revised_result, _ = interpret(raw, "abstention_review")
        if revised_result is None:
            # Invalid second output is a technical error, not evidence absence.
            return validate_model_decision(revised_decision, retrieval)
        return select(revised_result)
    return select(first_result)
