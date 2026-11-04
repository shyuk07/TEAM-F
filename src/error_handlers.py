from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from auth.domain.exceptions import AuthenticationError, EmailDuplicatedError
from reservations.domain.exceptions import ReservationConflictError

_HTTP_CODES = {
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
}


def _body(error_code: str, message: str) -> dict:
    return {"success": False, "error_code": error_code, "message": message}


def _response(status_code: int, error_code: str, message: str, headers=None) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=_body(error_code, message), headers=headers)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AuthenticationError)
    async def authentication_error(request: Request, exc: AuthenticationError):
        return _response(401, exc.error_code, str(exc), {"WWW-Authenticate": "Bearer"})

    @app.exception_handler(EmailDuplicatedError)
    async def email_duplicated(request: Request, exc: EmailDuplicatedError):
        return _response(409, exc.error_code, str(exc))

    @app.exception_handler(ReservationConflictError)
    async def reservation_conflict(request: Request, exc: ReservationConflictError):
        return _response(409, exc.error_code, str(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "form")]
            field = ".".join(loc) or "요청"
            message = f"{field}: {first.get('msg', '')}"
        else:
            message = "요청 형식이 올바르지 않습니다."
        return _response(400, "VALIDATION_ERROR", message)

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError):
        return _response(400, getattr(exc, "error_code", "VALIDATION_ERROR"), str(exc))

    @app.exception_handler(PermissionError)
    async def permission_error(request: Request, exc: PermissionError):
        return _response(403, "FORBIDDEN", str(exc))

    @app.exception_handler(LookupError)
    async def lookup_error(request: Request, exc: LookupError):
        return _response(404, "NOT_FOUND", str(exc))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "HTTP_ERROR")
        return _response(exc.status_code, code, str(exc.detail), exc.headers)
