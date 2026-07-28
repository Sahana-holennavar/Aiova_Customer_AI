import React, { useState, useRef, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import { sendChatMessage, uploadChatFile, clearChat } from "../store/slices/complaintsSlice";

const severityMeta = {
  Critical: { pill: "pill-critical", ring: "#dc2626", soft: "#fef2f2" },
  Major: { pill: "pill-major", ring: "#d97706", soft: "#fffbeb" },
  Minor: { pill: "pill-minor", ring: "#16a34a", soft: "#f0fdf4" },
};

function TypingIndicator() {
  return (
    <div className="chat-msg assistant">
      <div className="chat-bubble">
        <div className="typing-dots">
          <span></span><span></span><span></span>
        </div>
      </div>
    </div>
  );
}

export default function AICopilotPanel() {
  const dispatch = useDispatch();
  const chatMessages = useSelector((s) => s.complaints.chatMessages);
  const isTyping = useSelector((s) => s.complaints.isTyping);
  const pipelineResult = useSelector((s) => s.complaints.pipelineResult);
  const activeComplaintId = useSelector((s) => s.complaints.activeComplaintId);

  const [input, setInput] = useState("");
  const fileRef = useRef(null);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, isTyping]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isTyping) return;
    setInput("");
    dispatch(sendChatMessage({ message: text, complaintId: activeComplaintId }));
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    dispatch(uploadChatFile({ file, message: "", complaintId: activeComplaintId }));
    e.target.value = "";
  };

  const handleNewComplaint = () => {
    dispatch(clearChat());
  };

  const risk = pipelineResult?.risk || {};
  const meta = severityMeta[risk.severity] || severityMeta.Minor;
  const rootCause = pipelineResult?.root_cause || {};
  const capa = pipelineResult?.capa || {};
  const completeness = pipelineResult?.completeness || {};
  const summary = pipelineResult?.summary;

  const showRiskPanel = !!pipelineResult;

  return (
    <div className="card chat-card">
      {/* ── Header ── */}
      <div className="card-header">
        <div>
          <div className="card-title">AIVOA AI Copilot</div>
          <div className="card-subtitle">
            Describe a complaint or upload a document — the AI will extract and triage it
          </div>
        </div>
        <button className="btn btn-secondary" onClick={handleNewComplaint} title="Start a new complaint">
          + New
        </button>
      </div>

      {/* ── Messages ── */}
      <div className="chat-messages">
        {chatMessages.length === 0 && (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">AI</div>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 4 }}>AIVOA AI Copilot</div>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
              I can help you log and manage pharmaceutical complaints.<br />
              Try saying:<br />
              <em>"Apollo Pharmacy reported discolored capsules in Amoxicillin 500mg, batch BMX-240602"</em><br />
              or upload a complaint document.
            </div>
          </div>
        )}

        {chatMessages.map((msg, i) => (
          <div key={i} className={`chat-msg ${msg.role}`}>
            <div className="chat-avatar">{msg.role === "assistant" ? "AI" : "You"}</div>
            <div className="chat-bubble">{msg.content}</div>
          </div>
        ))}

        {isTyping && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Risk Panel (inline, after analysis) ── */}
      {showRiskPanel && (
        <div className="chat-risk-panel">
          <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
            <div
              className="risk-score-ring"
              style={{ background: meta.soft, color: meta.ring, border: `3px solid ${meta.ring}33`, width: 56, height: 56, fontSize: 15 }}
            >
              {risk.risk_score ?? "--"}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 3 }}>
                <span className={`pill ${meta.pill}`}>{risk.severity || "Pending"}</span>
                {risk.is_adverse_event && (
                  <span className="pill pill-neutral" style={{ fontSize: 11 }}>AE: {risk.is_adverse_event}</span>
                )}
                {completeness.completeness_status && (
                  <span className={`pill ${completeness.completeness_status === "Complete" ? "pill-minor" : "pill-major"}`} style={{ fontSize: 11 }}>
                    {completeness.completeness_status}
                  </span>
                )}
              </div>
              <div className="small-muted" style={{ fontSize: 11 }}>{risk.rationale}</div>
            </div>
          </div>

          {summary && (
            <div className="copilot-section">
              <div className="copilot-section-title">Summary</div>
              <div style={{ fontSize: 12, lineHeight: 1.5 }}>{summary}</div>
            </div>
          )}

          {rootCause?.root_cause_hypotheses?.length > 0 && (
            <div className="copilot-section">
              <div className="copilot-section-title">Root Cause Hypotheses</div>
              <div className="chip-list">
                {rootCause.root_cause_hypotheses.map((h, i) => (
                  <div className="chip-item" key={i} style={{ fontSize: 12, padding: "5px 8px" }}>
                    <span className="num">{i + 1}</span> {h}
                  </div>
                ))}
              </div>
            </div>
          )}

          {(capa.corrective_actions?.length > 0 || capa.preventive_actions?.length > 0) && (
            <div className="copilot-section">
              <div className="copilot-section-title">
                CAPA {capa.capa_priority && <span className="pill pill-neutral" style={{ marginLeft: 6, fontSize: 10 }}>{capa.capa_priority}</span>}
              </div>
              <div className="chip-list">
                {capa.corrective_actions?.map((c, i) => (
                  <div className="chip-item" key={`c${i}`} style={{ fontSize: 12, padding: "5px 8px" }}>
                    <span className="num">CA</span> {c}
                  </div>
                ))}
                {capa.preventive_actions?.map((p, i) => (
                  <div className="chip-item" key={`p${i}`} style={{ fontSize: 12, padding: "5px 8px" }}>
                    <span className="num">PA</span> {p}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Input Area ── */}
      <div className="chat-input-area">
        <input
          type="file"
          ref={fileRef}
          style={{ display: "none" }}
          accept=".pdf,.eml,.txt,.png,.jpg,.jpeg"
          onChange={handleFileSelect}
        />
        <button
          className="chat-attach-btn"
          onClick={() => fileRef.current?.click()}
          title="Upload complaint document"
        >
          &#128206;
        </button>
        <textarea
          className="chat-input"
          rows={1}
          placeholder={activeComplaintId ? "Edit the complaint (e.g. 'Batch number is BMX-240602')..." : "Describe a complaint (e.g. 'Apollo Pharmacy reported discolored capsules...')"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isTyping}
        />
        <button
          className="btn btn-primary chat-send-btn"
          onClick={handleSend}
          disabled={!input.trim() || isTyping}
        >
          Send
        </button>
      </div>
    </div>
  );
}
