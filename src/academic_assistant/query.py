"""Orquestração do fluxo de consulta, sem responsabilidades de interface."""

from langchain_core.embeddings import Embeddings

from academic_assistant.config import Settings
from academic_assistant.generation import (
    InvokableModel,
    create_chat_model,
    generate_answer,
)
from academic_assistant.indexing import create_embeddings
from academic_assistant.retrieval import (
    RetrievalContext,
    applicable_document_ids,
    retrieve_from_active_index,
    resolve_context,
)
from academic_assistant.validation import AnswerResult, insufficient_evidence_result


def answer_question(
    question: str,
    context: RetrievalContext,
    settings: Settings | None = None,
    *,
    embeddings: Embeddings | None = None,
    model: InvokableModel | None = None,
) -> AnswerResult:
    """Recupera, gera e valida uma resposta reutilizando o índice ativo."""
    if not question or not question.strip():
        raise ValueError("A pergunta não pode ser vazia.")
    active_settings = settings or Settings()
    context = resolve_context(context)
    applicable_document_ids(active_settings, context)
    active_embeddings = embeddings or create_embeddings(active_settings)
    retrieval = retrieve_from_active_index(
        question,
        active_settings,
        active_embeddings,
        context,
    )
    if not retrieval.evidences:
        return insufficient_evidence_result()
    active_model = model or create_chat_model(active_settings)
    return generate_answer(retrieval, active_model)
