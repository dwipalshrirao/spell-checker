import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from database import Base


class CheckRequest(Base):
    __tablename__ = "check_requests"

    id = Column(Integer, primary_key=True, index=True)
    correlation_id = Column(String(36), index=True, nullable=False)
    original_text = Column(Text, nullable=False)
    corrected_text = Column(Text, nullable=True)
    model = Column(String(64), nullable=False)
    error_count = Column(Integer, default=0)
    latency_ms = Column(Float, nullable=True)
    status = Column(String(16), default="pending")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
