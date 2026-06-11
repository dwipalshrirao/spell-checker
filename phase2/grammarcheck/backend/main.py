import logging
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
from middleware.correlation_id import CorrelationIDMiddleware
from middleware.rate_limiter import RateLimitMiddleware
from middleware.request_logger import RequestLogMiddleware
from routers.check import router as check_router
from routers.feedback import router as feedback_router
from routers.health import router as health_router
from routers.metrics import router as metrics_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("grammarcheck")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    logger.info(
        "GrammarCheck backend started — model=%s db=%s",
        settings.ollama_model,
        settings.database_url,
    )
    yield


app = FastAPI(
    title="GrammarCheck API",
    version="2.0.0",
    description="Privacy-first grammar & spelling checker powered by local Ollama models.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(RateLimitMiddleware)

app.include_router(check_router, tags=["check"])
app.include_router(health_router, tags=["health"])
app.include_router(feedback_router, prefix="/feedback", tags=["feedback"])
app.include_router(metrics_router, tags=["metrics"])


@app.get("/")
async def root():
    return {"app": "GrammarCheck", "version": "2.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower(),
    )
