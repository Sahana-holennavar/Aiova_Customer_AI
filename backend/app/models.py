import uuid
import datetime as dt
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Float, JSON, Integer
from sqlalchemy.orm import relationship
from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class Complaint(Base):
    """
    Core complaint record used by the AI intake workflow and QA review form.
    """
    __tablename__ = "complaints"

    id = Column(String(36), primary_key=True, default=gen_id)
    complaint_number = Column(String(32), unique=True, index=True)

    # Intake / source
    source_channel = Column(String(50))
    raw_source_text = Column(Text)

    # Customer / product details
    customer_name = Column(String(255))
    customer_contact = Column(String(255))
    product_name = Column(String(255))
    product_type = Column(String(50))
    batch_lot_number = Column(String(100))
    manufacturing_date = Column(String(50))
    expiry_date = Column(String(50))
    quantity_affected = Column(String(100))
    date_of_occurrence = Column(String(50))
    complaint_category = Column(String(100))
    complaint_description = Column(Text)
    country = Column(String(100))
    priority = Column(String(20), default="Medium")
    investigation_status = Column(String(30), default="Open")
    reviewer = Column(String(255))
    review_notes = Column(Text)

    # AI-derived fields
    ai_severity = Column(String(20))
    ai_risk_score = Column(Float)
    ai_risk_rationale = Column(Text)
    ai_is_adverse_event = Column(String(10))
    ai_completeness_status = Column(String(20))
    ai_missing_fields = Column(JSON)
    ai_root_cause_suggestions = Column(JSON)
    ai_capa_suggestions = Column(JSON)
    ai_summary = Column(Text)
    ai_duplicate_of = Column(String(36), nullable=True)
    ai_duplicate_score = Column(Float, nullable=True)

    status = Column(String(30), default="Draft")
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
    updated_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc), onupdate=lambda: dt.datetime.now(dt.timezone.utc))

    attachments = relationship("Attachment", back_populates="complaint", cascade="all, delete-orphan")


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(String(36), primary_key=True, default=gen_id)
    complaint_id = Column(String(36), ForeignKey("complaints.id"))
    filename = Column(String(255))
    file_type = Column(String(50))
    extracted_text = Column(Text)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))

    complaint = relationship("Complaint", back_populates="attachments")


class AgentRunLog(Base):
    """Audit trail of each LangGraph run for traceability."""
    __tablename__ = "agent_run_logs"

    id = Column(String(36), primary_key=True, default=gen_id)
    complaint_id = Column(String(36), ForeignKey("complaints.id"))
    node_name = Column(String(100))
    input_snapshot = Column(JSON)
    output_snapshot = Column(JSON)
    model_used = Column(String(100))
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=lambda: dt.datetime.now(dt.timezone.utc))
