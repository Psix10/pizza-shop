# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.db import init_models, init_seed
from api.support_router import router as support_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await init_seed()
    yield


app = FastAPI(title="Support Chat Service", lifespan=lifespan)

app.include_router(support_router)

@app.get("/health")
def health():
    return {"status": "ok"}