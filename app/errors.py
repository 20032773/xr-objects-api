"""統一錯誤回應格式的 exception handlers（spec 4）。"""
import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.errors")

_STATUS_CODE_MAP: dict[int, str] = {
    400: "BAD_REQUEST",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    422: "VALIDATION_ERROR",
    500: "INTERNAL_ERROR",
}

_DEFAULT_MESSAGES: dict[int, str] = {
    404: "Not found",
    405: "Method not allowed",
    422: "Request validation failed",
    500: "Internal server error",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details or []}},
        headers=headers,
    )


def _convert_errors(errors: Any) -> list[dict[str, Any]]:
    """只保留 loc / msg / type，確保可序列化（不輸出 ctx / input）。"""
    out: list[dict[str, Any]] = []
    for err in errors:
        raw_loc = err.get("loc", ()) if isinstance(err, dict) else ()
        loc: list[str | int] = [
            item if isinstance(item, (str, int)) and not isinstance(item, bool) else str(item)
            for item in raw_loc
        ]
        out.append(
            {
                "loc": loc,
                "msg": str(err.get("msg", "")) if isinstance(err, dict) else str(err),
                "type": str(err.get("type", "value_error")) if isinstance(err, dict) else "value_error",
            }
        )
    return out


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = _convert_errors(exc.errors())
    if not details:
        details = [{"loc": ["body"], "msg": "Invalid request", "type": "value_error"}]
    return error_response(422, "VALIDATION_ERROR", "Request validation failed", details)


_BODY_PARSE_ERROR_DETAIL = "There was an error parsing the body"


def _is_body_parse_error(exc: StarletteHTTPException) -> bool:
    """FastAPI 在 body 無法解析（例如非合法 UTF-8）時會丟出 400 並帶固定 detail。"""
    if exc.status_code != 400:
        return False
    return exc.detail == _BODY_PARSE_ERROR_DETAIL or isinstance(exc.__cause__, UnicodeDecodeError)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    if _is_body_parse_error(exc):
        # spec §4/§5.1：body 解析失敗一律 422 VALIDATION_ERROR
        msg = (
            "Request body is not valid UTF-8"
            if isinstance(exc.__cause__, UnicodeDecodeError)
            else "JSON decode error"
        )
        return error_response(
            422,
            "VALIDATION_ERROR",
            "Request validation failed",
            [{"loc": ["body"], "msg": msg, "type": "json_invalid"}],
        )
    status = exc.status_code
    code = _STATUS_CODE_MAP.get(status, "HTTP_ERROR" if status < 500 else "INTERNAL_ERROR")
    if status >= 500:
        message = "Internal server error"
    else:
        detail = exc.detail
        message = detail if isinstance(detail, str) and detail else _DEFAULT_MESSAGES.get(status, "Error")
    headers = dict(exc.headers) if getattr(exc, "headers", None) else None
    return error_response(status, code, message, [], headers=headers)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error while processing %s %s", request.method, request.url.path)
    return error_response(500, "INTERNAL_ERROR", "Internal server error", [])


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
