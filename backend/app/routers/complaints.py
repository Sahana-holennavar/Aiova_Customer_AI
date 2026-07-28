import random
import string
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


def generate_complaint_number(db: Session) -> str:
    year = dt.datetime.now(dt.timezone.utc).year
    for _ in range(10):
        suffix = "".join(random.choices(string.digits, k=8))
        number = f"CMP-{year}-{suffix}"
        existing = db.query(models.Complaint).filter(models.Complaint.complaint_number == number).first()
        if not existing:
            return number
    # Fallback: use timestamp-based suffix
    suffix = str(int(dt.datetime.now(dt.timezone.utc).timestamp()))[-8:]
    return f"CMP-{year}-{suffix}"


@router.post("", response_model=schemas.ComplaintOut)
def create_complaint(payload: schemas.ComplaintCreate, db: Session = Depends(get_db)):
    complaint = models.Complaint(
        complaint_number=generate_complaint_number(db),
        status="Logged",
        **payload.model_dump(exclude_unset=True, exclude_none=True),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("", response_model=list[schemas.ComplaintOut])
def list_complaints(db: Session = Depends(get_db), limit: int = 50):
    return db.query(models.Complaint).order_by(desc(models.Complaint.created_at)).limit(limit).all()


@router.get("/{complaint_id}", response_model=schemas.ComplaintOut)
def get_complaint(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    return complaint


@router.put("/{complaint_id}", response_model=schemas.ComplaintOut)
def update_complaint(complaint_id: str, payload: schemas.ComplaintUpdate, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    for k, v in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(complaint, k, v)
    complaint.updated_at = dt.datetime.now(dt.timezone.utc)
    db.commit()
    db.refresh(complaint)
    return complaint


@router.delete("/{complaint_id}")
def delete_complaint(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    db.delete(complaint)
    db.commit()
    return {"ok": True}
