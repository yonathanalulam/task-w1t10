from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import get_settings, settings_for_log
from app.core.database import SessionLocal
from app.core.logging import configure_logging
from app.services.bootstrap import ensure_bootstrap_state


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    with SessionLocal() as db:
        ensure_bootstrap_state(db)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": settings.app_name,
        "environment": settings_for_log(),
        "docs": "/docs",
    }
