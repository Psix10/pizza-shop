from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.internal_events_router import router as internal_events_router
from api.notification_router import router as notification_router
from db.db import init_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    yield


app = FastAPI(title="Notification Service", lifespan=lifespan)

app.include_router(internal_events_router)
app.include_router(notification_router)


@app.get("/health")
def health():
    return {"status": "ok"}