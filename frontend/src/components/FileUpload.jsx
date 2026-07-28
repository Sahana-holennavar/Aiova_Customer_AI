import React, { useState, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import { analyzeComplaintUpload, analyzeComplaintText } from "../store/slices/complaintsSlice";

export default function FileUpload() {
  const dispatch = useDispatch();
  const status = useSelector((s) => s.complaints.status);
  const error = useSelector((s) => s.complaints.error);
  const [dragActive, setDragActive] = useState(false);
  const [pastedText, setPastedText] = useState("");
  const [mode, setMode] = useState("upload"); // upload | paste
  const inputRef = useRef(null);

  const handleFile = (file) => {
    if (!file) return;
    dispatch(analyzeComplaintUpload(file));
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    handleFile(file);
  };

  const onSubmitPaste = () => {
    if (!pastedText.trim()) return;
    dispatch(analyzeComplaintText({ text: pastedText, sourceChannel: "email" }));
  };

  const isAnalyzing = status === "analyzing";

  return (
    <div className="card">
      <div className="card-header">
        <div>
          <div className="card-title">Complaint Intake</div>
          <div className="card-subtitle">
            Upload a complaint PDF/email, or paste the text — the AI agent will extract & triage it
          </div>
        </div>
        <div className="tabs">
          <button className={`tab ${mode === "upload" ? "active" : ""}`} onClick={() => setMode("upload")}>
            Upload File
          </button>
          <button className={`tab ${mode === "paste" ? "active" : ""}`} onClick={() => setMode("paste")}>
            Paste Text
          </button>
        </div>
      </div>

      {mode === "upload" ? (
        <div>
          {error && (
            <div style={{ background: "var(--critical-soft)", color: "var(--critical)", padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, border: "1px solid var(--critical)", fontWeight: 500 }}>
              {error}
            </div>
          )}
          <div
            className={`dropzone ${dragActive ? "active" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragActive(true);
            }}
            onDragLeave={() => setDragActive(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            style={{ cursor: "pointer" }}
          >
            <input
              ref={inputRef}
              type="file"
              hidden
              accept=".pdf,.eml,.txt,.png,.jpg,.jpeg"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {isAnalyzing ? (
              <div>⏳ Running AI extraction &amp; risk triage pipeline…</div>
            ) : (
              <div>
                <strong>Drag &amp; drop</strong> a complaint PDF or email (.eml/.txt), or click to browse
                <div className="small-muted" style={{ marginTop: 6 }}>
                  Supported: PDF, EML, TXT, PNG/JPG (image OCR is out of scope for this demo)
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div>
          {error && (
            <div style={{ background: "var(--critical-soft)", color: "var(--critical)", padding: "10px 14px", borderRadius: 8, fontSize: 13, marginBottom: 12, border: "1px solid var(--critical)", fontWeight: 500 }}>
              {error}
            </div>
          )}
          <textarea
            rows={7}
            style={{ width: "100%", border: "1px solid var(--border)", borderRadius: 8, padding: 10, fontSize: 13.5 }}
            placeholder="Paste the raw complaint email or notes here…"
            value={pastedText}
            onChange={(e) => setPastedText(e.target.value)}
          />
          <div style={{ marginTop: 10, display: "flex", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" onClick={onSubmitPaste} disabled={isAnalyzing}>
              {isAnalyzing ? "Analyzing…" : "Run AI Extraction"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
