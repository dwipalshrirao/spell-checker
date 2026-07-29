from pydantic import BaseModel, Field


class CheckRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class Error(BaseModel):
    original: str
    corrected: str
    type: str
    reason: str


class CheckResponse(BaseModel):
    corrected_text: str
    errors: list[Error]
    summary: str
    model: str
    latency_ms: float | None = None


class FeedbackCreate(BaseModel):
    request_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str | None = None


class HealthResponse(BaseModel):
    status: str
    model: str
    ollama_reachable: bool
    uptime_seconds: float | None = None


class MetricsResponse(BaseModel):
    total_requests: int
    total_errors_found: int
    avg_latency_ms: float
    p95_latency_ms: float
    model: str
