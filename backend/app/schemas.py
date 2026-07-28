from pydantic import BaseModel
from typing import Optional, List
import datetime as dt


class ComplaintCreate(BaseModel):
    source_channel: Optional[str] = "manual"
    raw_source_text: Optional[str] = None
    customer_name: Optional[str] = None
    customer_contact: Optional[str] = None
    product_name: Optional[str] = None
    product_type: Optional[str] = None
    batch_lot_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    quantity_affected: Optional[str] = None
    date_of_occurrence: Optional[str] = None
    complaint_category: Optional[str] = None
    complaint_description: Optional[str] = None
    country: Optional[str] = None
    priority: Optional[str] = None
    investigation_status: Optional[str] = None
    reviewer: Optional[str] = None
    review_notes: Optional[str] = None
    # AI-derived fields (editable by reviewer before logging)
    ai_severity: Optional[str] = None
    ai_risk_score: Optional[float] = None
    ai_risk_rationale: Optional[str] = None
    ai_is_adverse_event: Optional[str] = None
    ai_completeness_status: Optional[str] = None
    ai_missing_fields: Optional[List[str]] = None
    ai_root_cause_suggestions: Optional[List[str]] = None
    ai_capa_suggestions: Optional[List[str]] = None
    ai_summary: Optional[str] = None


class ComplaintUpdate(ComplaintCreate):
    status: Optional[str] = None


class AIAssessment(BaseModel):
    ai_severity: Optional[str] = None
    ai_risk_score: Optional[float] = None
    ai_risk_rationale: Optional[str] = None
    ai_is_adverse_event: Optional[str] = None
    ai_completeness_status: Optional[str] = None
    ai_missing_fields: Optional[List[str]] = None
    ai_root_cause_suggestions: Optional[List[str]] = None
    ai_capa_suggestions: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    ai_duplicate_of: Optional[str] = None
    ai_duplicate_score: Optional[float] = None


class ComplaintOut(ComplaintCreate, AIAssessment):
    id: str
    complaint_number: Optional[str]
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime

    class Config:
        from_attributes = True


class AnalyzeTextRequest(BaseModel):
    text: str
    source_channel: str = "email"
