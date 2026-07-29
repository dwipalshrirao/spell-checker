import time

from fastapi import APIRouter

from config import settings
from models.request_models import HealthResponse
from services.grammar_service import GrammarService

router = APIRouter()
_start_time = time.monotonic()


@router.get("/health", response_model=HealthResponse)
async def health():
    svc = GrammarService()
    ollama_up = await svc.check_ollama_running()
    await svc.close()
    return HealthResponse(
        status="ok" if ollama_up else "degraded",
        model=settings.ollama_model,
        ollama_reachable=ollama_up,
        uptime_seconds=round(time.monotonic() - _start_time, 1),
    )


@router.get("/ready")
async def ready():
    svc = GrammarService()
    ollama_up = await svc.check_ollama_running()
    await svc.close()
    if not ollama_up:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "detail": "Ollama not reachable"},
        )
    return {"status": "ready"}
