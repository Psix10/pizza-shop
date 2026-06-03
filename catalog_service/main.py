# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.correlation import correlation_id_middleware
from db.db import init_models, init_seed
from routers.catalog_router import router as catalog_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await init_seed()
    yield


app = FastAPI(title="Catalog Service", lifespan=lifespan)
app.middleware("http")(correlation_id_middleware)

app.include_router(catalog_router)

@app.get("/health")
def health():
    return {"status": "ok"}