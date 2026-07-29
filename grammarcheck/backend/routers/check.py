import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.db_models import CheckRequest as CheckRequestDB
from models.request_models import CheckRequest, CheckResponse, Error
from services.cache_service import CacheService
from services.grammar_service import GrammarService
from services.guardrail_service import GuardrailService

logger = logging.getLogger("grammarcheck")

router = APIRouter()


def get_check_deps() -> tuple:
    return GuardrailService(), GrammarService(), CacheService()


@router.post("/check", response_model=CheckResponse)
async def check_text(
    body: CheckRequest,
    db: Session = Depends(get_db),
    services: tuple = Depends(get_check_deps),
):
    guardrail, grammar_service, cache = services

    guardrail.validate_input(body.text)

    model = settings.ollama_model

    cached = cache.get(body.text, model)
    if cached:
        result = cached
    else:
        result = await grammar_service.check(body.text)
        cache.set(body.text, model, result)

    errors_data = result.get("errors", [])
    errors = [Error(**e) for e in errors_data]

    record = CheckRequestDB(
        correlation_id="pending",
        original_text=body.text,
        corrected_text=result.get("corrected_text", ""),
        model=model,
        error_count=len(errors),
        latency_ms=result.get("_latency_ms"),
        status="completed",
    )
    db.add(record)
    db.commit()

    response = CheckResponse(
        corrected_text=result.get("corrected_text", ""),
        errors=errors,
        summary=result.get("summary", ""),
        model=model,
        latency_ms=result.get("_latency_ms"),
    )
    return response
