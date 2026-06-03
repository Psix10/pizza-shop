# gateway/proxy.py
import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from services.routing import resolve_service
from core.config import API_PREFIX
from services.proxy_service import build_forward_headers 
GATEWAY_TIMEOUT = 10.0  # можно взять из env

async def forward_request(
    request: Request,
    path: str,
    auth_context: dict | None,
) -> StreamingResponse:
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

            upstream_response = await client.send(upstream_request, stream=True)

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

            return StreamingResponse(
                upstream_response.aiter_raw(),
                status_code=upstream_response.status_code,
                headers=response_headers,
                background=BackgroundTask(upstream_response.aclose),
            )

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream service unavailable: {exc}",
        ) from exc