"""Interface HTTP local; a consulta e sua validação pertencem ao núcleo RAG."""

from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from academic_assistant.config import Settings
from academic_assistant.generation import GenerationError, GenerationProviderError
from academic_assistant.indexing import IndexingError, load_corpus_selection
from academic_assistant.query import answer_question
from academic_assistant.rate_limit import RateLimiter, RateLimitSettings, RateLimitStorageError
from academic_assistant.retrieval import (
    ContextNotCoveredError,
    ContextRequiredError,
    RetrievalContext,
    RetrievalError,
)
from academic_assistant.validation import AnswerResult, GenerationValidationError


STATIC_DIR = Path(__file__).with_name("static")
Answerer = Callable[[str, RetrievalContext, Settings], AnswerResult]


class QueryContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    institution: Literal["IFMA"] = "IFMA"
    course_level: str = Field(min_length=1, max_length=200)
    campus: str | None = Field(default=None, max_length=200)
    modality: str | None = Field(default=None, max_length=200)

    @field_validator("campus", "modality")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None


class QueryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=4_000)
    context: QueryContext


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def create_app(
    settings: Settings | None = None,
    *,
    answerer: Answerer = answer_question,
) -> FastAPI:
    """Permite testar HTTP com uma função de consulta local, sem provedor real."""
    active_settings = settings or Settings()
    limiter = RateLimiter(RateLimitSettings.from_env(
        active_settings.index_dir.parent / "web" / "rate-limits.sqlite3"
    ))
    app = FastAPI(title="Assistente de regulamentos acadêmicos", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def private_responses(request: Request, call_next):
        response = await call_next(request)
        # Respostas e perguntas não devem permanecer no cache do navegador.
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'none'; form-action 'self'"
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        # Não devolver o corpo da pergunta nos detalhes da validação.
        return error_response(
            422, "invalid_request",
            "Confira a pergunta (até 4.000 caracteres) e selecione o nível do curso.",
        )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/context")
    def available_context():
        try:
            documents = load_corpus_selection(active_settings).values()
        except IndexingError:
            return error_response(
                503, "corpus_unavailable",
                "Não foi possível carregar o cadastro dos documentos. Confira o inventário local no servidor.",
            )

        def options(field: str) -> list[str]:
            return sorted({
                value.strip() for item in documents
                if isinstance(value := item.get(field), str) and value.strip()
            }, key=str.casefold)

        return {
            "institution": "IFMA",
            "course_levels": options("course_level"),
            "campuses": options("campus"),
            "modalities": options("modality"),
        }

    @app.post("/api/ask")
    def ask(payload: QueryRequest, request: Request):
        try:
            retry_after = limiter.consume(request.client.host if request.client else "unknown")
        except RateLimitStorageError:
            return error_response(
                503, "rate_limit_unavailable",
                "O controle de consultas está indisponível. Tente novamente mais tarde.",
            )
        if retry_after:
            response = error_response(
                429, "rate_limited",
                f"Limite de consultas atingido. Aguarde {retry_after} segundos antes de tentar novamente.",
            )
            response.headers["Retry-After"] = str(retry_after)
            return response
        context = RetrievalContext(**payload.context.model_dump())
        try:
            result = answerer(payload.question, context, active_settings)
        except (ContextRequiredError, ContextNotCoveredError, ValueError) as error:
            return error_response(422, "invalid_context", str(error))
        except IndexingError:
            return error_response(
                503, "index_unavailable",
                "O índice ou sua configuração está indisponível. Confira as credenciais, o inventário e a indexação no servidor.",
            )
        except RetrievalError:
            return error_response(
                502, "retrieval_failed",
                "Não foi possível buscar os trechos dos documentos. Tente novamente; se persistir, confira o índice e o provedor no servidor.",
            )
        except GenerationValidationError:
            return error_response(
                502, "invalid_generation",
                "A resposta não passou pela validação e não foi exibida. Tente fazer a pergunta novamente.",
            )
        except GenerationProviderError:
            return error_response(
                502, "provider_failed",
                "O serviço de geração não concluiu a consulta. Tente novamente em instantes.",
            )
        except GenerationError:
            return error_response(
                503, "generation_unavailable",
                "Não foi possível preparar a geração. Confira a configuração e as credenciais no servidor.",
            )
        return asdict(result)

    return app


app = create_app()
