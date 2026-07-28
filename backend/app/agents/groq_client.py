"""
Thin wrapper around the Groq SDK with resilient fallbacks for demos and local runs.
"""
import os
import json
import time
from typing import Optional, List, Dict, Any
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY", "").strip()
try:
    _client = Groq(api_key=api_key) if api_key else None
except TypeError:
    _client = None
except Exception:
    _client = None

PRIMARY_MODEL = os.getenv("GROQ_MODEL_PRIMARY", "gemma2-9b-it")
FALLBACK_MODEL = os.getenv("GROQ_MODEL_FALLBACK", "llama-3.3-70b-versatile")


def _heuristic_fallback(required_keys: Optional[List[str]] = None, user_prompt: str = "") -> Dict[str, Any]:
    if not required_keys:
        return {"status": "fallback"}

    lower_text = user_prompt.lower()
    if "completeness_status" in required_keys:
        return {
            "completeness_status": "Incomplete",
            "missing_fields": ["product_name", "batch_lot_number", "complaint_description"],
            "reviewer_note": "Fallback heuristic used because the LLM service was unavailable.",
        }
    if "severity" in required_keys:
        return {
            "severity": "Minor",
            "risk_score": 32,
            "is_adverse_event": "No",
            "rationale": "Fallback heuristic used because the LLM service was unavailable.",
        }
    if "root_cause_hypotheses" in required_keys:
        return {
            "root_cause_hypotheses": ["Packaging or labeling error", "Process deviation during handling", "Insufficient batch traceability"],
            "recommended_investigation_steps": ["Inspect packaging materials", "Review manufacturing records", "Confirm lot traceability"],
        }
    if "corrective_actions" in required_keys:
        return {
            "corrective_actions": ["Review affected lots and packaging materials"],
            "preventive_actions": ["Strengthen incoming inspection checks"],
            "capa_priority": "Medium",
        }
    if "summary" in required_keys:
        return {"summary": "Complaint intake captured for review. Additional QA follow-up is recommended."}
    if "customer_name" in required_keys:
        return {
            "customer_name": None,
            "customer_contact": None,
            "product_name": None,
            "product_type": None,
            "batch_lot_number": None,
            "manufacturing_date": None,
            "expiry_date": None,
            "quantity_affected": None,
            "date_of_occurrence": None,
            "complaint_category": "Other",
            "complaint_description": lower_text[:280],
        }
    return {}


def _coerce_json(raw: str) -> Optional[Dict[str, Any]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start_idx = raw.find("{")
        end_idx = raw.rfind("}")
        if start_idx == -1 or end_idx <= start_idx:
            return None
        try:
            parsed = json.loads(raw[start_idx:end_idx + 1])
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None


def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.2,
    required_keys: Optional[List[str]] = None,
    fallback_payload: Optional[Dict[str, Any]] = None,
) -> tuple[Dict[str, Any], str, str, int, Optional[Dict[str, int]]]:
    """
    Calls Groq chat completion and returns parsed JSON. If the LLM is unavailable,
    a deterministic fallback payload is returned so the workflow still runs.
    """
    selected_model = model or PRIMARY_MODEL
    start = time.time()
    usage: Optional[Dict[str, int]] = None

    if not _client:
        parsed = fallback_payload or _heuristic_fallback(required_keys, user_prompt)
        return parsed, "[fallback]", selected_model, 0, usage

    for attempt in range(2):
        try:
            resp = _client.chat.completions.create(
                model=selected_model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
            )
            raw = getattr(resp.choices[0].message, "content", "") or ""
            if getattr(resp, "usage", None):
                usage = {
                    "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
                    "completion_tokens": getattr(resp.usage, "completion_tokens", None),
                    "total_tokens": getattr(resp.usage, "total_tokens", None),
                }
            parsed = _coerce_json(raw)
            if parsed is None:
                continue
            if required_keys and not all(key in parsed for key in required_keys):
                continue
            duration_ms = int((time.time() - start) * 1000)
            return parsed, raw, selected_model, duration_ms, usage
        except Exception:
            if selected_model != FALLBACK_MODEL:
                selected_model = FALLBACK_MODEL
                continue
            break

    payload = fallback_payload or _heuristic_fallback(required_keys, user_prompt)
    duration_ms = int((time.time() - start) * 1000)
    return payload, "[fallback]", selected_model, duration_ms, usage
