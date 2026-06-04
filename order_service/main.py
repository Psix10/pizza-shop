from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.db import init_models
from routers.cart_router import router as cart_router
from routers.order_router import router as order_router
from routers.internal_orders_router import router as internal_orders_router
from routers.internal_outbox_router import router as internal_outbox_router
from common.correlation import correlation_id_middleware



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="Order Service", lifespan=lifespan)

app.middleware("http")(correlation_id_middleware)

app.include_router(cart_router, prefix="/api/v1")
app.include_router(order_router, prefix="/api/v1")
app.include_router(internal_orders_router, prefix="/api/v1")
app.include_router(internal_outbox_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}