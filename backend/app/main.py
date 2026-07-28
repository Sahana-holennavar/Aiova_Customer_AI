import os
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.database import Base, engine
from app.routers import complaints, ai

load_dotenv()

try:
    Base.metadata.create_all(bind=engine)
except Exception:
    pass

app = FastAPI(
    title="AIVOA Customer Complaint Management API",
    description="AI-powered complaint intake & triage for pharmaceutical API/FDF manufacturers.",
    version="1.0.0",
)

origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router)
app.include_router(ai.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"detail": "Unexpected server error", "error": str(exc)})


@app.get("/")
def health_check():
    return {"status": "ok", "service": "aivoa-complaint-api"}


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
