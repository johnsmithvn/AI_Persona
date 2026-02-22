"""
Custom exception classes + FastAPI exception handlers.

Contract:
- All errors produce a consistent JSON response format.
- No stacktraces leak to the client.
- Every error includes a correlation_id for log correlation.
"""

import uuid
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


# ─── Exception Classes ────────────────────────────────────────────────────────

class AppError(Exception):
    """Base class for all application-level errors."""

    def __init__(self, code: str, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class MemoryNotFoundError(AppError):
    def __init__(self, memory_id: str) -> None:
        super().__init__(
            code="MEMORY_NOT_FOUND",
            message=f"Memory with ID '{memory_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class DuplicateMemoryError(AppError):
    def __init__(self, checksum: str) -> None:
        super().__init__(
            code="DUPLICATE_MEMORY",
            message=f"Memory with checksum '{checksum}' already exists.",
            status_code=status.HTTP_409_CONFLICT,
        )


class EmbeddingFailedError(AppError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            code="EMBEDDING_FAILED",
            message=f"Embedding generation failed. {detail}".strip(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class LLMTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="LLM_TIMEOUT",
            message="LLM request timed out.",
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        )


class LLMError(AppError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            code="LLM_ERROR",
            message=f"LLM request failed. {detail}".strip(),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class RetrievalError(AppError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(
            code="RETRIEVAL_ERROR",
            message=f"Retrieval failed. {detail}".strip(),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class TokenBudgetExceededError(AppError):
    def __init__(self) -> None:
        super().__init__(
            code="TOKEN_BUDGET_EXCEEDED",
            message="Context token budget exceeded after trimming.",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class InvalidModeError(AppError):
    def __init__(self, mode: str) -> None:
        valid = "RECALL, RECALL_LLM_RERANK, SYNTHESIZE, REFLECT, CHALLENGE, EXPAND"
        super().__init__(
            code="INVALID_MODE",
            message=f"Invalid mode '{mode}'. Must be one of: {valid}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class PolicyViolationError(AppError):
    """Raised when LLM response violates mode policy (e.g. no citations when required)."""
    def __init__(self, mode: str, violation: str) -> None:
        super().__init__(
            code="POLICY_VIOLATION",
            message=f"[{mode}] Policy violation: {violation}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


# ─── Response Builder ─────────────────────────────────────────────────────────

def _error_response(
    code: str,
    message: str,
    status_code: int,
    correlation_id: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id or str(uuid.uuid4()),
            }
        },
    )


# ─── FastAPI Handler Registration ─────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to the FastAPI app."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        return _error_response(exc.code, exc.message, exc.status_code, correlation_id)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
        # Never leak internal details
        return _error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            correlation_id=correlation_id,
        )
