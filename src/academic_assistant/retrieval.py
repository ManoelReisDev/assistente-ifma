"""Recuperação rastreável de evidências no índice ativo, sem chamar um LLM."""

from dataclasses import dataclass, replace
from datetime import date
import re
import unicodedata
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from academic_assistant.config import Settings
from academic_assistant.indexing import (
    LoadedIndex,
    load_active_index,
    load_corpus_selection,
)


class RetrievalError(RuntimeError):
    """A busca não pôde ser executada ou produziu dados inválidos."""


class ContextRequiredError(ValueError):
    """Faltam dados mínimos para selecionar o corpus aplicável."""


class ContextNotCoveredError(ValueError):
    """O corpus selecionado não cobre o contexto informado."""


@dataclass(frozen=True, slots=True)
class RetrievalContext:
    institution: str | None = "IFMA"
    course_level: str | None = None
    campus: str | None = None
    modality: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievedEvidence:
    source_id: str
    document_id: str
    document_name: str
    document_hash: str
    page_number: int
    chunk_id: str
    excerpt: str
    is_primary: bool
    distance: float | None
    publication_date: str | None = None
    precedence_group: str | None = None

    def __post_init__(self) -> None:
        validate_precedence_metadata(self.publication_date, self.precedence_group)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    question: str
    context: RetrievalContext
    evidences: tuple[RetrievedEvidence, ...]
    limitations: tuple[str, ...]

    @property
    def source_map(self) -> dict[str, RetrievedEvidence]:
        return {evidence.source_id: evidence for evidence in self.evidences}

    @property
    def superseded_source_ids(self) -> frozenset[str]:
        """Descarta versões anteriores somente em grupos integralmente datados."""
        return _superseded_versions({
            item.source_id: (item.publication_date, item.precedence_group)
            for item in self.evidences
        })


def _superseded_versions(versions: dict[str, tuple[str | None, str | None]]) -> frozenset[str]:
    groups: dict[str, dict[str, str | None]] = {}
    for identifier, (published, group) in versions.items():
        if group:
            groups.setdefault(group, {})[identifier] = published
    superseded = set()
    for items in groups.values():
        if any(published is None for published in items.values()):
            continue
        latest = max(published for published in items.values() if published is not None)
        superseded.update(identifier for identifier, published in items.items()
                          if published is not None and published < latest)
    return frozenset(superseded)


def validate_precedence_metadata(publication_date: Any, precedence_group: Any) -> None:
    """Valida metadados curados; não infere data ou substituição pelo texto."""
    if publication_date is not None:
        if not isinstance(publication_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", publication_date):
            raise RetrievalError("publication_date deve usar uma data válida no formato YYYY-MM-DD.")
        try:
            date.fromisoformat(publication_date)
        except ValueError as error:
            raise RetrievalError("publication_date contém uma data inválida.") from error
    if precedence_group is not None and (
        not isinstance(precedence_group, str) or not precedence_group.strip()
    ):
        raise RetrievalError("precedence_group deve ser um identificador não vazio.")


def resolve_context(context: RetrievalContext) -> RetrievalContext:
    """Assume IFMA quando omitido; outros dados acadêmicos continuam explícitos."""
    if not context.institution or not context.institution.strip():
        return replace(context, institution="IFMA")
    return context


def _normalized(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_accents.casefold()).strip()


def _institution_id(document: dict[str, Any]) -> str | None:
    explicit = document.get("institution_id")
    if isinstance(explicit, str) and explicit.strip():
        return _normalized(explicit)
    institution = document.get("institution")
    if not isinstance(institution, str):
        return None
    normalized = _normalized(institution)
    if "ifma" in normalized or normalized == (
        "instituto federal de educacao ciencia e tecnologia do maranhao"
    ):
        return "ifma"
    return normalized


def _matches_optional(document_value: Any, requested_value: str | None) -> bool:
    if document_value is None:
        return True
    if not isinstance(document_value, str) or not document_value.strip():
        return True
    return requested_value is not None and _normalized(document_value) == _normalized(requested_value)


def _resolve_scope(
    settings: Settings, context: RetrievalContext
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    context = resolve_context(context)
    missing = []
    if not context.course_level or not context.course_level.strip():
        missing.append("nível do curso")
    if missing:
        raise ContextRequiredError(
            "Informe " + " e ".join(missing) + " para selecionar os documentos aplicáveis."
        )

    requested_institution = _normalized(context.institution)
    if requested_institution in {
        "instituto federal de educacao ciencia e tecnologia do maranhao",
        "instituto federal do maranhao",
    }:
        requested_institution = "ifma"
    if requested_institution != "ifma":
        raise ContextNotCoveredError("Este assistente atende exclusivamente ao IFMA.")

    selected = load_corpus_selection(settings)
    applicable = []
    limitations_by_id = {}
    group_scopes: dict[str, tuple[str, ...]] = {}
    for document_id, document in selected.items():
        institution_id = _institution_id(document)
        course_level = document.get("course_level")
        if institution_id is None or not isinstance(course_level, str) or not course_level.strip():
            raise RetrievalError(
                f"Documento {document_id} sem contexto institucional mínimo no inventário."
            )
        if institution_id != requested_institution:
            continue
        if _normalized(course_level) != _normalized(context.course_level):
            continue
        if not _matches_optional(document.get("campus"), context.campus):
            continue
        if not _matches_optional(document.get("modality"), context.modality):
            continue
        validate_precedence_metadata(document.get("publication_date"), document.get("precedence_group"))
        group = document.get("precedence_group")
        if group:
            scope = (
                institution_id, _normalized(course_level),
                _normalized(document.get("campus") or ""),
                _normalized(document.get("modality") or ""),
            )
            if group in group_scopes and group_scopes[group] != scope:
                raise RetrievalError("Grupo de precedência mistura escopos; revise o inventário.")
            group_scopes[group] = scope
        applicable.append(document_id)
        limitation = document.get("applicability_limits")
        if isinstance(limitation, str) and limitation.strip():
            limitations_by_id[document_id] = f"{document_id}: {limitation.strip()}"

    if not applicable:
        raise ContextNotCoveredError(
            "Os documentos cadastrados não cobrem o contexto informado."
        )
    superseded = _superseded_versions({
        document_id: (selected[document_id].get("publication_date"), selected[document_id].get("precedence_group"))
        for document_id in applicable
    })
    current = [document_id for document_id in applicable if document_id not in superseded]
    limitations = [value for key, value in limitations_by_id.items() if key in current]
    replaced_groups = {selected[key]["precedence_group"] for key in superseded}
    for document_id in current:
        document = selected[document_id]
        if document.get("precedence_group") in replaced_groups:
            limitations.append(
                f"Fonte priorizada: {document.get('document_name', document_id)} "
                f"({document['publication_date']}), por ser a versão mais recente do grupo revisado."
            )
    return tuple(sorted(current)), tuple(dict.fromkeys(limitations))


def applicable_document_ids(
    settings: Settings, context: RetrievalContext
) -> tuple[str, ...]:
    """Resolve o escopo consultável sem usar semelhança textual como aplicabilidade."""
    document_ids, _ = _resolve_scope(settings, context)
    return document_ids


def _metadata_filter(document_ids: tuple[str, ...]) -> dict[str, Any]:
    if len(document_ids) == 1:
        return {"document_id": document_ids[0]}
    return {"document_id": {"$in": list(document_ids)}}


def _validate_document(document: Document) -> None:
    required = (
        "document_id",
        "document_name",
        "document_hash",
        "page_number",
        "chunk_id",
    )
    if any(field not in document.metadata for field in required):
        raise RetrievalError("O índice retornou um trecho sem metadados obrigatórios.")
    if not document.page_content:
        raise RetrievalError("O índice retornou um trecho sem conteúdo.")


def _neighbor_documents(
    loaded: LoadedIndex,
    primary_documents: list[Document],
    settings: Settings,
    document_ids: tuple[str, ...],
) -> list[Document]:
    if settings.retrieval_page_window == 0:
        return []
    pages_by_document: dict[str, set[int]] = {}
    allowed = set(document_ids)
    for document in primary_documents:
        document_id = document.metadata.get("document_id")
        page_number = document.metadata.get("page_number")
        if document_id not in allowed or not isinstance(page_number, int):
            raise RetrievalError("O índice retornou metadados de origem inválidos.")
        pages = pages_by_document.setdefault(document_id, set())
        start = max(1, page_number - settings.retrieval_page_window)
        pages.update(range(start, page_number + settings.retrieval_page_window + 1))

    neighbors: list[Document] = []
    try:
        for document_id in sorted(pages_by_document):
            pages = sorted(pages_by_document[document_id])
            result = loaded.store.get(
                where={
                    "$and": [
                        {"document_id": document_id},
                        {"page_number": {"$in": pages}},
                    ]
                },
                include=["documents", "metadatas"],
            )
            texts = result.get("documents") or []
            metadatas = result.get("metadatas") or []
            if len(texts) != len(metadatas):
                raise RetrievalError("O índice retornou contexto vizinho inconsistente.")
            neighbors.extend(
                Document(page_content=text, metadata=metadata)
                for text, metadata in zip(texts, metadatas)
            )
    except RetrievalError:
        raise
    except Exception as error:
        raise RetrievalError("Falha ao recuperar o contexto das páginas vizinhas.") from error
    return sorted(
        neighbors,
        key=lambda item: (
            item.metadata.get("document_id", ""),
            item.metadata.get("page_number", 0),
        ),
    )


def retrieve_evidence(
    question: str,
    loaded: LoadedIndex,
    settings: Settings,
    context: RetrievalContext,
) -> RetrievalResult:
    """Busca evidências e atribui IDs apenas a trechos reais do índice."""
    if not question or not question.strip():
        raise ValueError("A pergunta não pode ser vazia.")
    context = resolve_context(context)
    document_ids, limitations = _resolve_scope(settings, context)
    inventory = load_corpus_selection(settings)
    try:
        matches = loaded.store.similarity_search_with_score(
            question.strip(),
            k=settings.retrieval_k,
            filter=_metadata_filter(document_ids),
        )
    except Exception as error:
        raise RetrievalError("Falha ao buscar evidências no índice ativo.") from error

    primary_documents: list[Document] = []
    distances: dict[str, float] = {}
    for document, distance in matches:
        _validate_document(document)
        if document.metadata["document_id"] not in document_ids:
            raise RetrievalError("O índice retornou um documento fora do contexto aplicável.")
        chunk_id = document.metadata["chunk_id"]
        if chunk_id not in distances:
            primary_documents.append(document)
            distances[chunk_id] = float(distance)

    neighbors = _neighbor_documents(loaded, primary_documents, settings, document_ids)
    ordered: list[tuple[Document, bool, float | None]] = [
        (document, True, distances[document.metadata["chunk_id"]])
        for document in primary_documents
    ]
    seen = {document.metadata["chunk_id"] for document in primary_documents}
    for document in neighbors:
        _validate_document(document)
        chunk_id = document.metadata["chunk_id"]
        if chunk_id in seen:
            continue
        ordered.append((document, False, None))
        seen.add(chunk_id)
        if len(ordered) >= settings.retrieval_max_chunks:
            break

    evidences = tuple(
        RetrievedEvidence(
            source_id=str(position),
            document_id=document.metadata["document_id"],
            document_name=document.metadata["document_name"],
            document_hash=document.metadata["document_hash"],
            page_number=document.metadata["page_number"],
            chunk_id=document.metadata["chunk_id"],
            excerpt=document.page_content,
            is_primary=is_primary,
            distance=distance,
            publication_date=inventory[document.metadata["document_id"]].get("publication_date"),
            precedence_group=inventory[document.metadata["document_id"]].get("precedence_group"),
        )
        for position, (document, is_primary, distance) in enumerate(ordered, start=1)
    )
    return RetrievalResult(
        question=question.strip(),
        context=context,
        evidences=evidences,
        limitations=limitations,
    )


def retrieve_from_active_index(
    question: str,
    settings: Settings,
    embeddings: Embeddings,
    context: RetrievalContext,
) -> RetrievalResult:
    """Diagnóstico completo: carrega o índice e recupera sem geração por LLM."""
    loaded = load_active_index(settings, embeddings)
    return retrieve_evidence(question, loaded, settings, context)
