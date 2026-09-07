"""UFMS API entry point.

    uvicorn app.main:app --reload
    docs at http://127.0.0.1:8000/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_log import RequestLogMiddleware

configure_logging()
logger = logging.getLogger("ufms")

app = FastAPI(
    title=settings.app_name,
    description=(
        "Decision support for preventive municipal maintenance. "
        "Ranks a city's known failure points by tonight's risk, flags "
        "locations becoming failures before they reach the official "
        "register, and measures whether past interventions worked."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/", tags=["health"])
def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "api": settings.api_v1_prefix,
    }


@app.on_event("startup")
def _startup() -> None:
    logger.info("%s starting in %s mode", settings.app_name, settings.environment)
