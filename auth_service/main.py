from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from api.auth_router import router as auth_router


from db.db import init_models, async_session, init_seed
from services.admin_seed import seed_rbac
from common.correlation import correlation_id_middleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_models()
    await init_seed()
    async with async_session() as session:
        await seed_rbac(session)


    yield



app = FastAPI(title="Admin Service", lifespan=lifespan)

app.middleware("http")(correlation_id_middleware)

origins = [
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router)



@app.get("/health")
def health():
    return {"status": "ok"}