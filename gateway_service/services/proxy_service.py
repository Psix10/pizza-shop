from typing import Any

import httpx
from fastapi import HTTPException, Request
from fastapi.responses import Response

from common.correlation import CORRELATION_HEADER
from .routing import resolve_service


GATEWAY_TIMEOUT = 10.0


def build_forward_headers(
    request: Request,
    auth_context: dict[str, Any] | None,
) -> dict[str, str]:
    headers: dict[str, str] = {}

    for key, value in request.headers.items():
        if key.lower() in {"host", "content-length"}:
            continue
        headers[key] = value

    if auth_context:
        user_id = str(auth_context.get("sub") or "")
        if user_id:
            headers["x-user-id"] = user_id

    correlation_id = getattr(request.state, "correlation_id", None)
    if correlation_id:
        headers[CORRELATION_HEADER] = correlation_id

    return headers


async def forward_request(
    request: Request,
    path: str,
    auth_context: dict[str, Any] | None,
) -> Response:
    target_base = resolve_service(path)

    url = httpx.URL(
        path=path,
        query=request.url.query.encode("utf-8"),
    )

    headers = build_forward_headers(request, auth_context)

    try:
        async with httpx.AsyncClient(
            base_url=target_base,
            timeout=GATEWAY_TIMEOUT,
        ) as client:
            upstream_request = client.build_request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
            )

            upstream_response = await client.send(
                upstream_request,
                stream=False,
            )

            excluded_headers = {
                "content-encoding",
                "transfer-encoding",
                "connection",
            }

            response_headers = {
                key: value
                for key, value in upstream_response.headers.items()
                if key.lower() not in excluded_headers
            }

            return Response(
                content=upstream_response.content,
                status_code=upstream_response.status_code,
                headers=response_headers,
            )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream service unavailable: {exc}",
        ) from exc