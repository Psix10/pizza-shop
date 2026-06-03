import uuid
from fastapi import Request


CORRELATION_HEADER = "X-Correlation-ID"


async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get(CORRELATION_HEADER) or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers[CORRELATION_HEADER] = correlation_id
    return response


def get_correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)