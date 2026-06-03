# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.db import init_models, init_seed
from routers.store_routers import router as store_router
from common.correlation import correlation_id_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await init_seed()
    yield


app = FastAPI(title="Store Service", lifespan=lifespan)
app.middleware("http")(correlation_id_middleware)
app.include_router(store_router)

@app.get("/health")
def health():
    return {"status": "ok"}