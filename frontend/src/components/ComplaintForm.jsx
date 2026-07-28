import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { updateDraftField, saveComplaintEdits, fetchComplaints, clearDraft } from "../store/slices/complaintsSlice";

const FIELD_DEFS = [
  { key: "complaint_number", label: "Complaint ID", readOnly: true },
  { key: "customer_name", label: "Customer" },
  { key: "customer_contact", label: "Customer Contact" },
  { key: "product_name", label: "Product" },
  { key: "product_type", label: "Product Type", type: "select", options: ["", "API", "FDF"] },
  { key: "batch_lot_number", label: "Batch Number" },
  { key: "manufacturing_date", label: "Manufacturing Date" },
  { key: "expiry_date", label: "Expiry Date" },
  { key: "quantity_affected", label: "Quantity Affected" },
  { key: "date_of_occurrence", label: "Complaint Date" },
  { key: "country", label: "Country" },
  { key: "ai_severity", label: "Severity", type: "select", options: ["", "Critical", "Major", "Minor"] },
  { key: "priority", label: "Priority", type: "select", options: ["", "High", "Medium", "Low"] },
  { key: "ai_risk_score", label: "Risk Score", readOnly: true },
  { key: "ai_is_adverse_event", label: "Adverse Event", readOnly: true },
  { key: "investigation_status", label: "Investigation Status", type: "select", options: ["", "Open", "Pending", "Closed"] },
  { key: "reviewer", label: "Reviewer" },
  { key: "complaint_category", label: "Complaint Category", type: "select", options: ["", "Quality Defect", "Packaging Defect", "Adverse Event", "Documentation Error", "Delivery/Shipping", "Counterfeit Suspected", "Other"] },
  { key: "status", label: "Status", type: "select", options: ["", "Draft", "Logged", "Under Investigation", "CAPA Assigned", "Closed"] },
];

function fieldIsFlagged(missingFields, label) {
  if (!missingFields) return false;
  return missingFields.some((m) => m.toLowerCase().includes(label.toLowerCase().split(" ")[0]));
}

export default function ComplaintForm() {
  const dispatch = useDispatch();
  const draft = useSelector((s) => s.complaints.activeDraft);
  const pipelineResult = useSelector((s) => s.complaints.pipelineResult);
  const error = useSelector((s) => s.complaints.error);
  const missingFields = pipelineResult?.completeness?.missing_fields || [];

  if (!draft) {
    return (
      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Log Customer Complaint</div>
            <div className="card-subtitle">Fields will auto-populate once a complaint is analyzed</div>
          </div>
        </div>
        <div className="empty-state">No complaint loaded yet. Upload a file or paste complaint text on the left to begin.</div>
      </div>
    );
  }

  const onChange = (key, value) => {
    dispatch(updateDraftField({ field: key, value }));
  };

  const onSave = async () => {
    const payload = { ...draft };
    delete payload.id;
    await dispatch(saveComplaintEdits({ id: draft.id, payload }));
    dispatch(fetchComplaints());
  };

  const onDiscard = () => {
    dispatch(clearDraft());
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">Log Customer Complaint</div>
          <div className="card-subtitle">Auto-extracted by AI — review, correct, and confirm before logging</div>
        </div>
        {pipelineResult?.completeness?.completeness_status && (
          <span className={`pill ${pipelineResult.completeness.completeness_status === "Complete" ? "pill-minor" : "pill-major"}`}>
            {pipelineResult.completeness.completeness_status}
          </span>
        )}
      </div>

      <div className="field-grid">
        {FIELD_DEFS.map((f) => {
          const flagged = fieldIsFlagged(missingFields, f.label);
          const value = draft[f.key] ?? "";
          return (
            <div className="field" key={f.key}>
              <label>
                {f.label}
                {flagged && <span style={{ color: "var(--major)" }}> • needs review</span>}
              </label>
              {f.type === "select" ? (
                <select
                  className={flagged ? "field-flag" : ""}
                  value={value}
                  onChange={(e) => onChange(f.key, e.target.value)}
                  disabled={f.readOnly}
                >
                  {f.options.map((o) => (
                    <option key={o} value={o}>{o || "Select…"}</option>
                  ))}
                </select>
              ) : (
                <input
                  className={flagged ? "field-flag" : ""}
                  value={value}
                  onChange={(e) => onChange(f.key, e.target.value)}
                  placeholder="—"
                  readOnly={f.readOnly}
                  tabIndex={f.readOnly ? -1 : 0}
                  style={f.readOnly ? { background: "#f8f9fb", color: "var(--text-secondary)", cursor: "default" } : {}}
                />
              )}
            </div>
          );
        })}

        <div className="field full">
          <label>Complaint Description</label>
          <textarea rows={4} value={draft.complaint_description || ""} onChange={(e) => onChange("complaint_description", e.target.value)} />
        </div>

        <div className="field full">
          <label>Review Notes</label>
          <textarea rows={3} value={draft.review_notes || ""} onChange={(e) => onChange("review_notes", e.target.value)} />
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        {error && (
          <div style={{ background: "var(--critical-soft)", color: "var(--critical)", padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, border: "1px solid var(--critical)", fontWeight: 500 }}>
            {error}
          </div>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
          <button className="btn btn-secondary" onClick={onDiscard}>Discard</button>
          <button className="btn btn-primary" onClick={onSave}>Save &amp; Log Complaint</button>
        </div>
      </div>
    </div>
  );
}
