from fastapi import FastAPI

from common.correlation import correlation_id_middleware
from routers.api import router as api_router

app = FastAPI(title="Gateway Service")
app.middleware("http")(correlation_id_middleware)

app.include_router(api_router)