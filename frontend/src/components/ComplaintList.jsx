import React, { useEffect, useMemo, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { fetchComplaints, setActiveDraft, setPipelineResult } from "../store/slices/complaintsSlice";

const sevPill = { Critical: "pill-critical", Major: "pill-major", Minor: "pill-minor" };

export default function ComplaintList() {
  const dispatch = useDispatch();
  const list = useSelector((s) => s.complaints.list);
  const [query, setQuery] = useState("");

  useEffect(() => {
    dispatch(fetchComplaints());
  }, [dispatch]);

  const filtered = useMemo(() => {
    const q = query.toLowerCase();
    return list.filter((c) => `${c.complaint_number || ""} ${c.product_name || ""} ${c.customer_name || ""}`.toLowerCase().includes(q));
  }, [list, query]);

  const loadComplaint = (c) => {
    dispatch(setActiveDraft({ ...c }));
    dispatch(setPipelineResult({
      risk: {
        severity: c.ai_severity,
        risk_score: c.ai_risk_score,
        rationale: c.ai_risk_rationale,
        is_adverse_event: c.ai_is_adverse_event,
      },
      completeness: {
        completeness_status: c.ai_completeness_status,
        missing_fields: c.ai_missing_fields,
      },
      root_cause: {
        root_cause_hypotheses: c.ai_root_cause_suggestions,
      },
      capa: {
        corrective_actions: c.ai_capa_suggestions,
        preventive_actions: [],
      },
      summary: c.ai_summary,
      duplicate: {
        is_duplicate: !!c.ai_duplicate_of,
        duplicate_of_id: c.ai_duplicate_of,
        similarity_score: c.ai_duplicate_score,
      },
      trace: [],
    }));
  };

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">Recent Complaints</div>
          <div className="card-subtitle">{list.length} logged</div>
        </div>
        <button className="btn btn-secondary" onClick={() => dispatch(fetchComplaints())}>Refresh</button>
      </div>

      <input className="search-box" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search complaints" />

      {filtered.length === 0 ? (
        <div className="empty-state">No complaints match the current filter.</div>
      ) : (
        <div>
          {filtered.map((c) => (
            <div className="list-row" key={c.id} onClick={() => loadComplaint(c)}>
              <div>
                <div style={{ fontWeight: 600 }}>{c.complaint_number || "Pending number"}</div>
                <div className="small-muted">{c.product_name || "Unknown product"} · {c.batch_lot_number || "no batch"}</div>
                <div className="small-muted">{c.customer_name || "Unknown customer"}</div>
              </div>
              <span className={`pill ${sevPill[c.ai_severity] || "pill-neutral"}`}>{c.ai_severity || "Unclassified"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
