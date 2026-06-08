from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI

from api.delivery_router import router as delivery_router
from db.db import init_models
from services.event_consumer import DeliveryEventConsumer
from services.outbox_publisher import outbox_worker  # новый воркер


consumer = DeliveryEventConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()

    # стартуем consumer входящих событий
    await consumer.start()

    # стартуем фонового воркера outbox
    outbox_task = asyncio.create_task(outbox_worker())

    try:
        yield
    finally:
        # корректно останавливаемся
        outbox_task.cancel()
        await consumer.close()


app = FastAPI(
    title="Delivery Service",
    lifespan=lifespan,
)

app.include_router(delivery_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}