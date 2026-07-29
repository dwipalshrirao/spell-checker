from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.db_models import Feedback as FeedbackDB
from models.request_models import FeedbackCreate

router = APIRouter()


@router.post("", status_code=201)
def submit_feedback(body: FeedbackCreate, db: Session = Depends(get_db)):
    record = FeedbackDB(
        request_id=body.request_id,
        rating=body.rating,
        comment=body.comment,
    )
    db.add(record)
    db.commit()
    return {"status": "ok", "id": record.id}
