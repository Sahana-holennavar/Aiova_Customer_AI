"""
Each function below is one LangGraph node. Every node reads from `state`,
performs a single-purpose AI task, and writes its result back into `state`.
"""
from app.agents.groq_client import call_llm_json, FALLBACK_MODEL


def extract_fields_node(state: dict) -> dict:
    system = (
        "You are a pharmaceutical QA data-entry assistant. Extract structured complaint fields from the complaint text. "
        "Return JSON with exactly these keys: customer_name, customer_contact, product_name, product_type, "
        "batch_lot_number, manufacturing_date, expiry_date, quantity_affected, date_of_occurrence, "
        "complaint_category, complaint_description."
    )
    user = f"RAW COMPLAINT TEXT:\n\"\"\"\n{state['raw_text']}\n\"\"\""
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        required_keys=["customer_name", "product_name", "complaint_description"],
        fallback_payload={"customer_name": None, "customer_contact": None, "product_name": None, "product_type": None, "batch_lot_number": None, "manufacturing_date": None, "expiry_date": None, "quantity_affected": None, "date_of_occurrence": None, "complaint_category": "Other", "complaint_description": state["raw_text"][:400]},
    )
    state["extracted_fields"] = parsed
    state.setdefault("trace", []).append({"node": "extract_fields", "model": model, "duration_ms": ms, "token_usage": usage})
    return state


def completeness_check_node(state: dict) -> dict:
    fields = state["extracted_fields"]
    system = (
        "You are a QA compliance checker. Decide whether the complaint has enough information to start an investigation. "
        "Respond with JSON: {\"completeness_status\": \"Complete\" or \"Incomplete\", \"missing_fields\": [...], \"reviewer_note\": \"...\"}."
    )
    user = f"EXTRACTED FIELDS:\n{fields}"
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        required_keys=["completeness_status", "missing_fields", "reviewer_note"],
    )
    state["completeness"] = parsed
    state.setdefault("trace", []).append({"node": "completeness_check", "model": model, "duration_ms": ms, "token_usage": usage})
    return state


def risk_classification_node(state: dict) -> dict:
    fields = state["extracted_fields"]
    system = (
        "You are an AI Copilot performing initial risk triage on a pharmaceutical complaint. "
        "Respond with JSON: {\"severity\": \"Critical\" or \"Major\" or \"Minor\", \"risk_score\": 0-100, \"is_adverse_event\": \"Yes\" or \"No\" or \"Uncertain\", \"rationale\": \"...\"}."
    )
    user = f"EXTRACTED FIELDS:\n{fields}\n\nORIGINAL TEXT:\n{state['raw_text']}"
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        required_keys=["severity", "risk_score", "is_adverse_event", "rationale"],
    )
    state["risk"] = parsed
    state.setdefault("trace", []).append({"node": "risk_classification", "model": model, "duration_ms": ms, "token_usage": usage})
    return state


def root_cause_node(state: dict) -> dict:
    fields = state["extracted_fields"]
    system = (
        "You are a senior pharmaceutical Quality investigator. Suggest the 3 most likely root cause hypotheses. "
        "Respond with JSON: {\"root_cause_hypotheses\": [...], \"recommended_investigation_steps\": [...]}"
    )
    user = f"EXTRACTED FIELDS:\n{fields}\n\nRISK ASSESSMENT:\n{state.get('risk')}"
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        model=FALLBACK_MODEL,
        required_keys=["root_cause_hypotheses", "recommended_investigation_steps"],
    )
    state["root_cause"] = parsed
    state.setdefault("trace", []).append({"node": "root_cause_analysis", "model": model, "duration_ms": ms, "token_usage": usage})
    return state


def capa_recommendation_node(state: dict) -> dict:
    system = (
        "You are a QA specialist drafting a preliminary CAPA recommendation. "
        "Respond with JSON: {\"corrective_actions\": [...], \"preventive_actions\": [...], \"capa_priority\": \"High\" or \"Medium\" or \"Low\"}."
    )
    user = (
        f"EXTRACTED FIELDS:\n{state['extracted_fields']}\n\n"
        f"RISK ASSESSMENT:\n{state.get('risk')}\n\n"
        f"ROOT CAUSE HYPOTHESES:\n{state.get('root_cause')}"
    )
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        required_keys=["corrective_actions", "preventive_actions", "capa_priority"],
    )
    state["capa"] = parsed
    state.setdefault("trace", []).append({"node": "capa_recommendation", "model": model, "duration_ms": ms, "token_usage": usage})
    return state


def duplicate_detection_node(state: dict) -> dict:
    recent = state.get("recent_complaints", [])
    if not recent:
        state["duplicate"] = {"is_duplicate": False, "duplicate_of_id": None, "similarity_score": 0, "reason": "No prior complaints to compare against."}
        state.setdefault("trace", []).append({"node": "duplicate_detection", "model": "skipped", "duration_ms": 0, "token_usage": None})
        return state

    system = (
        "You compare a new complaint against recent complaints to flag likely duplicates. "
        "Respond with JSON: {\"is_duplicate\": true/false, \"duplicate_of_id\": \"<id or null>\", \"similarity_score\": 0-100, \"reason\": \"...\"}."
    )
    user = (
        f"NEW COMPLAINT:\n{state['extracted_fields']}\n\n"
        f"EXISTING COMPLAINTS (id -> summary):\n{recent}"
    )
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        required_keys=["is_duplicate", "duplicate_of_id", "similarity_score", "reason"],
    )
    state["duplicate"] = parsed
    state.setdefault("trace", []).append({"node": "duplicate_detection", "model": model, "duration_ms": ms, "token_usage": usage})
    return state


def summary_node(state: dict) -> dict:
    system = (
        "Write a concise executive summary of the complaint suitable for a QA dashboard. "
        "Respond with JSON: {\"summary\": \"...\"}."
    )
    user = (
        f"FIELDS:\n{state['extracted_fields']}\n"
        f"SEVERITY:\n{state.get('risk', {}).get('severity')}\n"
    )
    parsed, _, model, ms, usage = call_llm_json(
        system,
        user,
        required_keys=["summary"],
    )
    state["summary"] = parsed.get("summary", "")
    state.setdefault("trace", []).append({"node": "summary_generation", "model": model, "duration_ms": ms, "token_usage": usage})
    return state
