import json
import random
import string
import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app import models
from app.utils.file_parser import extract_text
from app.agents.graph import run_complaint_pipeline
from app.agents.groq_client import call_llm_json

router = APIRouter(prefix="/api/ai", tags=["ai"])


# ── Helpers ──────────────────────────────────────────────────────────────────

def _recent_complaints_for_dupe_check(db: Session, limit: int = 15):
    rows = db.query(models.Complaint).order_by(desc(models.Complaint.created_at)).limit(limit).all()
    return [
        {
            "id": r.id,
            "product_name": r.product_name,
            "batch_lot_number": r.batch_lot_number,
            "summary": r.ai_summary or r.complaint_description,
        }
        for r in rows
    ]


def _generate_complaint_number(db: Session) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    for _ in range(10):
        suffix = "".join(random.choices(string.digits, k=8))
        number = f"CMP-{now.year}-{suffix}"
        if not db.query(models.Complaint).filter(models.Complaint.complaint_number == number).first():
            return number
    return f"CMP-{now.year}-{str(int(now.timestamp()))[-8:]}"


def _complaint_to_dict(c: models.Complaint) -> dict:
    """Serialize a Complaint model to a flat dict for LLM context."""
    return {
        "customer_name": c.customer_name,
        "customer_contact": c.customer_contact,
        "product_name": c.product_name,
        "product_type": c.product_type,
        "batch_lot_number": c.batch_lot_number,
        "manufacturing_date": c.manufacturing_date,
        "expiry_date": c.expiry_date,
        "quantity_affected": c.quantity_affected,
        "date_of_occurrence": c.date_of_occurrence,
        "complaint_category": c.complaint_category,
        "complaint_description": c.complaint_description,
        "country": c.country,
        "priority": c.priority,
    }


# ── Legacy pipeline persist (used by analyze-text / analyze-upload) ───────────

def _persist_pipeline_result(db: Session, raw_text: str, source_channel: str, result: dict) -> models.Complaint:
    fields = result.get("extracted_fields", {}) or {}
    risk = result.get("risk", {}) or {}
    completeness = result.get("completeness", {}) or {}
    root_cause = result.get("root_cause", {}) or {}
    capa = result.get("capa", {}) or {}
    duplicate = result.get("duplicate", {}) or {}

    complaint_number = _generate_complaint_number(db)

    complaint = models.Complaint(
        complaint_number=complaint_number,
        source_channel=source_channel,
        raw_source_text=raw_text,
        status="Logged",
        customer_name=fields.get("customer_name"),
        customer_contact=fields.get("customer_contact"),
        product_name=fields.get("product_name"),
        product_type=fields.get("product_type"),
        batch_lot_number=fields.get("batch_lot_number"),
        manufacturing_date=fields.get("manufacturing_date"),
        expiry_date=fields.get("expiry_date"),
        quantity_affected=fields.get("quantity_affected"),
        date_of_occurrence=fields.get("date_of_occurrence"),
        complaint_category=fields.get("complaint_category"),
        complaint_description=fields.get("complaint_description"),
        ai_severity=risk.get("severity"),
        ai_risk_score=risk.get("risk_score"),
        ai_risk_rationale=risk.get("rationale"),
        ai_is_adverse_event=risk.get("is_adverse_event"),
        ai_completeness_status=completeness.get("completeness_status"),
        ai_missing_fields=completeness.get("missing_fields"),
        ai_root_cause_suggestions=root_cause.get("root_cause_hypotheses"),
        ai_capa_suggestions=(capa.get("corrective_actions", []) + capa.get("preventive_actions", [])),
        ai_summary=result.get("summary"),
        ai_duplicate_of=duplicate.get("duplicate_of_id"),
        ai_duplicate_score=duplicate.get("similarity_score"),
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    for entry in result.get("trace", []):
        db.add(models.AgentRunLog(
            complaint_id=complaint.id,
            node_name=entry.get("node"),
            model_used=entry.get("model"),
            duration_ms=entry.get("duration_ms"),
            input_snapshot=None,
            output_snapshot=None,
        ))
    db.commit()
    return complaint


# ── Legacy endpoints ─────────────────────────────────────────────────────────

@router.post("/analyze-text")
def analyze_text(text: str = Form(...), source_channel: str = Form("manual"), db: Session = Depends(get_db)):
    if not text or not text.strip():
        raise HTTPException(400, "text is required")
    recent = _recent_complaints_for_dupe_check(db)
    result = run_complaint_pipeline(text, recent_complaints=recent)
    complaint = _persist_pipeline_result(db, text, source_channel, result)
    return {"complaint_id": complaint.id, "pipeline_result": result}


@router.post("/analyze-upload")
async def analyze_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_bytes = await file.read()
    text = extract_text(file.filename, file_bytes)
    if not text.strip():
        raise HTTPException(400, "Could not extract any text from the uploaded file")
    recent = _recent_complaints_for_dupe_check(db)
    result = run_complaint_pipeline(text, recent_complaints=recent)
    source_channel = "pdf_upload" if file.filename.lower().endswith(".pdf") else "email"
    complaint = _persist_pipeline_result(db, text, source_channel, result)
    db.add(models.Attachment(
        complaint_id=complaint.id,
        filename=file.filename,
        file_type=file.content_type,
        extracted_text=text,
    ))
    db.commit()
    return {"complaint_id": complaint.id, "pipeline_result": result}


@router.post("/reanalyze/{complaint_id}")
def reanalyze(complaint_id: str, db: Session = Depends(get_db)):
    complaint = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    recent = [c for c in _recent_complaints_for_dupe_check(db) if c["id"] != complaint_id]
    result = run_complaint_pipeline(complaint.raw_source_text or complaint.complaint_description or "", recent)
    risk = result.get("risk", {}) or {}
    completeness = result.get("completeness", {}) or {}
    capa = result.get("capa", {}) or {}
    duplicate = result.get("duplicate", {}) or {}
    complaint.ai_severity = risk.get("severity")
    complaint.ai_risk_score = risk.get("risk_score")
    complaint.ai_risk_rationale = risk.get("rationale")
    complaint.ai_is_adverse_event = risk.get("is_adverse_event")
    complaint.ai_completeness_status = completeness.get("completeness_status")
    complaint.ai_missing_fields = completeness.get("missing_fields")
    complaint.ai_root_cause_suggestions = result.get("root_cause", {}).get("root_cause_hypotheses")
    complaint.ai_capa_suggestions = capa.get("corrective_actions", []) + capa.get("preventive_actions", [])
    complaint.ai_summary = result.get("summary")
    complaint.ai_duplicate_of = duplicate.get("duplicate_of_id")
    complaint.ai_duplicate_score = duplicate.get("similarity_score")
    db.commit()
    db.refresh(complaint)
    return {"complaint_id": complaint.id, "pipeline_result": result}


# ══════════════════════════════════════════════════════════════════════════════
#  CHAT ENDPOINTS — primary interface for the AI Copilot
# ══════════════════════════════════════════════════════════════════════════════

def _run_chat_analysis(message: str, current_complaint: dict = None) -> dict:
    """Single LLM call that extracts fields, assesses risk, and generates a response."""
    context = ""
    if current_complaint:
        filtered = {k: v for k, v in current_complaint.items() if v is not None}
        if filtered:
            context = (
                "\nEXISTING COMPLAINT DATA — update ONLY the fields specifically "
                "mentioned by the user. Preserve every other field exactly as-is.\n"
                + json.dumps(filtered, indent=2) + "\n"
            )

    system = (
        "You are AIVOA AI Copilot, an expert pharmaceutical Quality Assurance assistant "
        "for a Customer Complaint Management system. You help users log, edit, and manage "
        "complaints for pharmaceutical API (Active Pharmaceutical Ingredient) and FDF "
        "(Finished Dosage Form) manufacturers.\n\n"
        "Based on the user's message:\n"
        "- If this is a NEW complaint: extract all available fields from the description.\n"
        "- If this is an EDIT to an existing complaint: update ONLY the fields specifically "
        "mentioned by the user, preserving all other existing data.\n"
        "- If the message is a greeting, question, or general help request: respond "
        "conversationally and set complaint_updates to null.\n\n"
        "Assess severity using pharma QA standards:\n"
        "- Critical: Patient safety risk, adverse events, potential recall.\n"
        "- Major: Significant quality defect, compliance impact, production disruption.\n"
        "- Minor: Cosmetic/packaging issue, no patient safety impact.\n\n"
        "Return a JSON object with exactly these keys:\n"
        "{\n"
        '  "response": "Brief friendly confirmation of what you extracted or updated",\n'
        '  "complaint_updates": {\n'
        '    "customer_name": null, "customer_contact": null,\n'
        '    "product_name": null, "product_type": null,\n'
        '    "batch_lot_number": null, "manufacturing_date": null,\n'
        '    "expiry_date": null, "quantity_affected": null,\n'
        '    "date_of_occurrence": null, "complaint_category": null,\n'
        '    "complaint_description": null, "country": null, "priority": null\n'
        "  },\n"
        '  "severity": "Critical or Major or Minor",\n'
        '  "risk_score": (number 0-100),\n'
        '  "is_adverse_event": "Yes or No or Uncertain",\n'
        '  "risk_rationale": "Brief rationale for severity classification",\n'
        '  "completeness_status": "Complete or Incomplete",\n'
        '  "missing_fields": ["list of missing important fields"],\n'
        '  "root_cause_hypotheses": ["hypothesis1", "hypothesis2", "hypothesis3"],\n'
        '  "corrective_actions": ["action1", "action2"],\n'
        '  "preventive_actions": ["action1", "action2"],\n'
        '  "capa_priority": "High or Medium or Low",\n'
        '  "summary": "One-paragraph executive summary of the complaint"\n'
        "}\n\n"
        "RULES:\n"
        "1. For complaint_updates: use null for fields NOT mentioned. Only set values you are confident about.\n"
        "2. For edits: confirm what was updated and what was preserved.\n"
        "3. For non-complaint messages: respond conversationally, set complaint_updates to null.\n"
        "4. product_type must be one of: null, \"API\", or \"FDF\".\n"
        "5. complaint_category must be one of: null, \"Quality Defect\", \"Packaging Defect\", "
        "\"Adverse Event\", \"Documentation Error\", \"Delivery/Shipping\", \"Counterfeit Suspected\", \"Other\".\n"
    )

    parsed, _, model, ms, usage = call_llm_json(
        system,
        context + "USER MESSAGE:\n" + message,
        required_keys=["response", "complaint_updates", "severity", "risk_score"],
        fallback_payload={
            "response": "I've logged your complaint. Some fields may need manual review.",
            "complaint_updates": {
                "complaint_description": message[:500],
                "complaint_category": "Other",
            },
            "severity": "Minor",
            "risk_score": 30,
            "is_adverse_event": "No",
            "risk_rationale": "Automated fallback — please review manually.",
            "completeness_status": "Incomplete",
            "missing_fields": ["product_name", "batch_lot_number", "customer_name"],
            "root_cause_hypotheses": ["Under investigation"],
            "corrective_actions": ["Review the complaint details"],
            "preventive_actions": ["Update intake procedures"],
            "capa_priority": "Medium",
            "summary": "Complaint received and logged for review.",
        },
    )
    return parsed


def _build_pipeline_result(updates: dict, analysis: dict, existing: dict = None) -> dict:
    """Merge extracted fields with analysis into the format the frontend expects."""
    merged = dict(existing) if existing else {}
    merged.update(updates)

    return {
        "extracted_fields": merged,
        "risk": {
            "severity": analysis.get("severity"),
            "risk_score": analysis.get("risk_score"),
            "rationale": analysis.get("risk_rationale"),
            "is_adverse_event": analysis.get("is_adverse_event"),
        },
        "completeness": {
            "completeness_status": analysis.get("completeness_status"),
            "missing_fields": analysis.get("missing_fields", []),
        },
        "root_cause": {
            "root_cause_hypotheses": analysis.get("root_cause_hypotheses", []),
        },
        "capa": {
            "corrective_actions": analysis.get("corrective_actions", []),
            "preventive_actions": analysis.get("preventive_actions", []),
            "capa_priority": analysis.get("capa_priority"),
        },
        "summary": analysis.get("summary"),
    }


def _upsert_complaint(
    db: Session, complaint_id: str, raw_text: str, pipeline_result: dict
) -> models.Complaint:
    """Create a new complaint or update an existing one from pipeline_result."""
    fields = pipeline_result.get("extracted_fields", {})
    risk = pipeline_result.get("risk", {})
    completeness = pipeline_result.get("completeness", {})
    root_cause = pipeline_result.get("root_cause", {})
    capa = pipeline_result.get("capa", {})

    complaint = None
    if complaint_id:
        complaint = (
            db.query(models.Complaint)
            .filter(models.Complaint.id == complaint_id)
            .first()
        )

    if complaint:
        # ── Update existing ──
        for k, v in fields.items():
            if hasattr(complaint, k) and v is not None:
                setattr(complaint, k, v)
        complaint.ai_severity = risk.get("severity")
        complaint.ai_risk_score = risk.get("risk_score")
        complaint.ai_risk_rationale = risk.get("rationale")
        complaint.ai_is_adverse_event = risk.get("is_adverse_event")
        complaint.ai_completeness_status = completeness.get("completeness_status")
        complaint.ai_missing_fields = completeness.get("missing_fields")
        complaint.ai_root_cause_suggestions = root_cause.get("root_cause_hypotheses")
        complaint.ai_capa_suggestions = capa.get("corrective_actions", []) + capa.get("preventive_actions", [])
        complaint.ai_summary = pipeline_result.get("summary")
        complaint.updated_at = dt.datetime.now(dt.timezone.utc)
        db.commit()
        db.refresh(complaint)
    else:
        # ── Create new ──
        complaint = models.Complaint(
            complaint_number=_generate_complaint_number(db),
            source_channel="chat",
            raw_source_text=raw_text,
            status="Logged",
            customer_name=fields.get("customer_name"),
            customer_contact=fields.get("customer_contact"),
            product_name=fields.get("product_name"),
            product_type=fields.get("product_type"),
            batch_lot_number=fields.get("batch_lot_number"),
            manufacturing_date=fields.get("manufacturing_date"),
            expiry_date=fields.get("expiry_date"),
            quantity_affected=fields.get("quantity_affected"),
            date_of_occurrence=fields.get("date_of_occurrence"),
            complaint_category=fields.get("complaint_category"),
            complaint_description=fields.get("complaint_description"),
            country=fields.get("country"),
            ai_severity=risk.get("severity"),
            ai_risk_score=risk.get("risk_score"),
            ai_risk_rationale=risk.get("rationale"),
            ai_is_adverse_event=risk.get("is_adverse_event"),
            ai_completeness_status=completeness.get("completeness_status"),
            ai_missing_fields=completeness.get("missing_fields"),
            ai_root_cause_suggestions=root_cause.get("root_cause_hypotheses"),
            ai_capa_suggestions=capa.get("corrective_actions", []) + capa.get("preventive_actions", []),
            ai_summary=pipeline_result.get("summary"),
        )
        db.add(complaint)
        db.commit()
        db.refresh(complaint)

    return complaint


@router.post("/chat")
def chat(
    message: str = Form(...),
    complaint_id: str = Form(None),
    db: Session = Depends(get_db),
):
    """Primary chat endpoint — accepts natural language, returns complaint + analysis."""
    if not message or not message.strip():
        raise HTTPException(400, "message is required")

    # Load existing complaint context if editing
    current = None
    if complaint_id:
        existing = (
            db.query(models.Complaint)
            .filter(models.Complaint.id == complaint_id)
            .first()
        )
        if existing:
            current = _complaint_to_dict(existing)

    # Single LLM call — extracts fields + risk assessment + response
    analysis = _run_chat_analysis(message, current)

    # Filter out null / empty updates (fields not mentioned)
    updates = analysis.get("complaint_updates") or {}
    updates = {k: v for k, v in updates.items() if v is not None and v != ""}

    if not updates:
        # Non-complaint conversational message
        return {
            "response": analysis.get("response", "How can I help you?"),
            "complaint_id": complaint_id,
            "pipeline_result": None,
        }

    # Build pipeline_result and persist to DB
    pipeline_result = _build_pipeline_result(updates, analysis, current)
    complaint = _upsert_complaint(db, complaint_id, message, pipeline_result)

    return {
        "response": analysis.get("response", "Complaint processed successfully."),
        "complaint_id": complaint.id,
        "pipeline_result": pipeline_result,
    }


@router.post("/chat-upload")
async def chat_upload(
    file: UploadFile = File(...),
    message: str = Form(""),
    complaint_id: str = Form(None),
    db: Session = Depends(get_db),
):
    """File upload via chat — extracts text then runs the same analysis."""
    file_bytes = await file.read()
    text = extract_text(file.filename, file_bytes)
    if not text.strip():
        raise HTTPException(400, "Could not extract text from the uploaded file")

    combined = text
    if message.strip():
        combined = f"{message}\n\n--- Extracted from {file.filename} ---\n{text}"

    # Load existing context if editing
    current = None
    if complaint_id:
        existing = (
            db.query(models.Complaint)
            .filter(models.Complaint.id == complaint_id)
            .first()
        )
        if existing:
            current = _complaint_to_dict(existing)

    analysis = _run_chat_analysis(combined, current)

    updates = analysis.get("complaint_updates") or {}
    updates = {k: v for k, v in updates.items() if v is not None and v != ""}

    if not updates:
        return {
            "response": analysis.get("response", "Document processed."),
            "complaint_id": complaint_id,
            "pipeline_result": None,
        }

    pipeline_result = _build_pipeline_result(updates, analysis, current)
    complaint = _upsert_complaint(db, complaint_id, combined, pipeline_result)

    db.add(models.Attachment(
        complaint_id=complaint.id,
        filename=file.filename,
        file_type=file.content_type,
        extracted_text=text,
    ))
    db.commit()

    return {
        "response": analysis.get("response", "Document extracted and complaint created."),
        "complaint_id": complaint.id,
        "pipeline_result": pipeline_result,
    }
