# main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI

from db.db import init_models, init_seed
from api.profile_router import router as profile_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await init_seed()
    yield


app = FastAPI(title="Profile Service", lifespan=lifespan)

app.include_router(profile_router)

@app.get("/health")
def health():
    return {"status": "ok"}