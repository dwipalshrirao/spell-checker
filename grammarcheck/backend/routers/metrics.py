from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.db_models import CheckRequest
from models.request_models import MetricsResponse

router = APIRouter()


@router.get("/metrics", response_model=MetricsResponse)
def metrics(db: Session = Depends(get_db)):
    total = db.query(func.count(CheckRequest.id)).scalar() or 0
    total_errors = db.query(func.sum(CheckRequest.error_count)).scalar() or 0
    avg_latency = (
        db.query(func.avg(CheckRequest.latency_ms)).scalar() or 0.0
    )

    latencies = [
        row[0]
        for row in db.query(CheckRequest.latency_ms)
        .filter(CheckRequest.latency_ms.isnot(None))
        .order_by(CheckRequest.latency_ms)
        .all()
    ]
    if latencies:
        idx = int(len(latencies) * 0.95)
        p95 = latencies[idx]
    else:
        p95 = 0.0

    return MetricsResponse(
        total_requests=total,
        total_errors_found=total_errors,
        avg_latency_ms=round(avg_latency, 1),
        p95_latency_ms=round(p95, 1),
        model=settings.ollama_model,
    )
