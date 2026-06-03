from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.delivery_router import router as delivery_router
from db.db import init_models
from services.event_consumer import DeliveryEventConsumer


consumer = DeliveryEventConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await consumer.start()
    yield
    await consumer.close()


app = FastAPI(
    title="Delivery Service",
    lifespan=lifespan,
)

app.include_router(delivery_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}