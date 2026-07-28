# AIVOA — AI-Powered Customer Complaint Management System

An AI-native Customer Complaint Management module for pharmaceutical **API** (Active
Pharmaceutical Ingredient) and **FDF** (Finished Dosage Form) manufacturers, built for
the AIVOA.AI Round 1 assignment.

A QA reviewer uploads a raw complaint (PDF, email, or pasted text) → a **LangGraph
agent pipeline** running on **Groq (gemma2-9b-it)** extracts structured fields, checks
completeness, classifies risk/severity, suggests root causes and CAPA, checks for
duplicates, and writes a summary → results populate the **Log Customer Complaint**
form and the **AI Copilot Risk Assessment** panel for human review.

> **Note on the reference demo video:** this build was implemented from the written
> assignment spec plus general pharma QMS/complaint-handling research, since the video
> content itself could not be reviewed frame-by-frame during generation. Please diff
> the UI copy/field names here against the actual demo video and adjust
> `frontend/src/components/ComplaintForm.jsx` (`FIELD_DEFS`) if any labels differ.

---

## Why it's built this way (design notes for the interview)

- **LangGraph, not one giant prompt.** The pipeline is 7 discrete nodes (extract →
  completeness → risk → root cause → CAPA → duplicate check → summary), each with a
  narrow, single-purpose prompt and its own JSON schema. This mirrors how a real QA
  reviewer works through a complaint step by step, makes each step independently
  testable/auditable (`AgentRunLog` table), and makes it easy to add branching later
  (e.g. skip CAPA generation on `Incomplete` records) without a rewrite.
- **Model choice per node.** Fast/cheap `gemma2-9b-it` handles extraction,
  classification, and summarization. `llama-3.3-70b-versatile` is used specifically
  for root-cause reasoning, where stronger multi-hypothesis reasoning matters more
  than latency — a deliberate trade-off, not a random switch.
- **Human-in-the-loop by design.** Every AI-populated field in the "Log Customer
  Complaint" form is editable before saving. CAPA/root-cause suggestions are labeled
  as *recommendations*, never auto-approved — consistent with 21 CFR Part 11 /
  ICH Q10 expectations that a qualified person reviews and signs off.
- **Traceability.** Every node run is logged (model used, duration) and shown in the
  "Agent Workflow Trace" section of the Copilot panel — useful both for the demo video
  walkthrough and for the audit-trail expectations of a real QMS.

---

## Tech stack (per assignment requirements)

| Layer | Technology |
|---|---|
| Frontend | React + Redux Toolkit, Google Inter font |
| Backend | Python, FastAPI |
| AI orchestration | LangGraph |
| LLMs | Groq — `gemma2-9b-it` (primary), `llama-3.3-70b-versatile` (root cause) |
| Database | PostgreSQL (MySQL also supported — just change `DATABASE_URL`) |

---

## Project structure

```
aivoa-complaint-system/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app entrypoint
│   │   ├── database.py            # SQLAlchemy engine/session
│   │   ├── models.py              # Complaint, Attachment, AgentRunLog
│   │   ├── schemas.py             # Pydantic request/response models
│   │   ├── agents/
│   │   │   ├── groq_client.py     # Groq SDK wrapper (JSON-mode + fallback model)
│   │   │   ├── nodes.py           # 7 LangGraph node functions (the AI logic)
│   │   │   └── graph.py           # StateGraph wiring the nodes together
│   │   ├── routers/
│   │   │   ├── complaints.py      # CRUD for logged complaints
│   │   │   └── ai.py              # /analyze-text, /analyze-upload, /reanalyze
│   │   └── utils/file_parser.py   # PDF/email/txt text extraction
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── FileUpload.jsx       # drag-drop / paste intake
│   │   │   ├── ComplaintForm.jsx    # editable "Log Customer Complaint" form
│   │   │   ├── AICopilotPanel.jsx   # AI Copilot Risk Assessment panel
│   │   │   └── ComplaintList.jsx    # recent complaints dashboard
│   │   ├── store/                   # Redux Toolkit slice + store
│   │   ├── api/client.js            # axios API layer
│   │   └── styles/index.css         # design tokens, Inter font
│   └── package.json
└── sample_data/                    # sample complaint PDF + 2 sample emails for demo
```

---

## Setup

### 1. Database

```bash
# Postgres example
createdb aivoa_complaints
```

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set GROQ_API_KEY (create one at https://console.groq.com) and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:3000 (proxies `/api` → `localhost:8000`)

---

## End-to-end workflow (what to show in the demo video)

1. **Intake** — On the "Complaint Intake" card, either drag in
   `sample_data/sample_complaint.pdf` (or the `.txt` samples) or paste text, and click
   **Run AI Extraction**.
   → Frontend: `FileUpload.jsx` dispatches `analyzeComplaintUpload` (Redux thunk)
   → API: `POST /api/ai/analyze-upload`
   → Backend: `file_parser.py` extracts raw text → `run_complaint_pipeline()`
   (`app/agents/graph.py`) executes the LangGraph pipeline.

2. **LangGraph pipeline** (`app/agents/nodes.py`), in order:
   `extract_fields` → `completeness_check` → `risk_classification` → `root_cause`
   → `capa_recommendation` → `duplicate_detection` → `summary`.
   Each node calls Groq via `groq_client.call_llm_json()` with a JSON-only prompt.

3. **Persistence** — `routers/ai.py::_persist_pipeline_result()` writes a new
   `Complaint` row plus an `AgentRunLog` entry per node.

4. **Form population** — The API response's `pipeline_result.extracted_fields`
   populates Redux `activeDraft`, which renders into **ComplaintForm.jsx**. Fields
   the completeness-checker flagged as missing are highlighted amber with a
   "needs review" note.

5. **AI Copilot panel** — `AICopilotPanel.jsx` renders severity/risk score,
   AI summary, completeness status, root-cause hypotheses, CAPA recommendation,
   duplicate-check result, and the full agent trace (model + latency per node).

6. **Review & log** — QA reviewer edits any field directly in the form and clicks
   **Save & Log Complaint** (`PUT /api/complaints/{id}`), then sees it appear in
   the **Recent Complaints** list.

7. **Duplicate detection demo** — Upload the same/similar complaint a second time
   to show the AI flagging it against the first (compares against the 15 most
   recent complaints).

---

## Bonus AI features implemented

- ✅ Complaint Completeness Checker
- ✅ AI Risk Classification (severity + risk score + adverse-event flag)
- ✅ Root Cause Recommendation
- ✅ CAPA Recommendation
- ✅ Duplicate Complaint Detection
- ✅ Complaint Summary
- ✅ Agent workflow trace / audit log (`AgentRunLog`) for traceability

## Explicitly out of scope (per assignment)

- Production-grade OCR (image uploads return a placeholder message)
- Auto-approval of CAPA/root cause — always requires human review
- Authentication/RBAC, e-signatures (would be needed for a real 21 CFR Part 11 system)

## Sample data

`sample_data/` contains a generated PDF complaint (Atorvastatin API, out-of-spec
impurity) and two email-style `.txt` complaints — one complete/critical
(Metformin API discoloration) and one deliberately incomplete/minor (damaged
packaging, no batch number) to demonstrate the completeness checker and severity
range in the demo.
"# Aiova_Customer_AI" 
