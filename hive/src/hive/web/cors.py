"""CORS policy for the Hive UI gateway."""

from collections.abc import Callable, Iterable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def headers_for(
    origin: str | None,
    allowed_origins: Iterable[str],
    methods: Iterable[str],
    allowed_headers: Iterable[str],
) -> dict[str, str] | None:
    if not origin or origin not in set(allowed_origins):
        return None
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": ", ".join(methods),
        "Access-Control-Allow-Headers": ", ".join(allowed_headers),
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


class ConfiguredCORSMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        allowed_origins: Callable[[Request], Iterable[str]],
        methods: Iterable[str],
        allowed_headers: Iterable[str],
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins
        self.methods = tuple(methods)
        self.allowed_headers = tuple(allowed_headers)

    async def dispatch(self, request: Request, call_next) -> Response:
        cors_headers = headers_for(
            request.headers.get("origin"),
            self.allowed_origins(request),
            self.methods,
            self.allowed_headers,
        )
        response = (
            Response(status_code=204) if request.method == "OPTIONS" and cors_headers else await call_next(request)
        )
        if cors_headers:
            response.headers.update(cors_headers)
        return response
