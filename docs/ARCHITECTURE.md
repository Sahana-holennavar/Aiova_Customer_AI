# Architecture Overview

## Components
- Frontend: React + Redux Toolkit + Vite
- Backend: FastAPI + SQLAlchemy
- AI: LangGraph nodes orchestrated via Groq-compatible JSON calls
- Data: SQLite by default for local demos, PostgreSQL/MySQL supported via DATABASE_URL

## Flow
1. Intake uploads or pasted text
2. Backend extracts structured complaint data
3. LangGraph runs the node pipeline
4. Results populate the complaint form and AI copilot panel
5. Reviewer saves the complaint and dashboard refreshes
