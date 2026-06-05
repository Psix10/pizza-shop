# main.py
from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from db.db import init_models
from routers.cart_router import router as cart_router
from routers.order_router import router as order_router
from routers.internal_orders_router import router as internal_orders_router
from routers.internal_outbox_router import router as internal_outbox_router
from common.correlation import correlation_id_middleware
from services.outbox_dispatcher import OutboxDispatcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()

    dispatcher = OutboxDispatcher(poll_interval=2.0, batch_size=50)
    task = asyncio.create_task(dispatcher.run_forever())

    app.state.outbox_dispatcher = dispatcher
    app.state.outbox_dispatcher_task = task

    try:
        yield
    finally:
        dispatcher.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Order Service", lifespan=lifespan)

app.middleware("http")(correlation_id_middleware)

app.include_router(cart_router)
app.include_router(order_router)
app.include_router(internal_orders_router)
app.include_router(internal_outbox_router)


@app.get("/health")
def health():
    return {"status": "ok"}