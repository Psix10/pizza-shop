from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.internal_events_router import router as internal_events_router
from api.kitchen_router import router as kitchen_router
from db.db import init_models, async_session
from services.event_consumer import KitchenEventConsumer
from common.correlation import correlation_id_middleware


consumer = KitchenEventConsumer(async_session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await consumer.start()
    yield
    await consumer.close()


app = FastAPI(title="Kitchen Service", lifespan=lifespan)
app.middleware("http")(correlation_id_middleware)

app.include_router(internal_events_router)
app.include_router(kitchen_router)


@app.get("/health")
def health():
    return {"status": "ok"}