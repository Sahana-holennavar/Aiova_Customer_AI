"""
Database engine/session setup.

Works with Postgres (recommended), MySQL, or SQLite for local demos.
If the configured database is unavailable, the app falls back to SQLite so the
workflow remains runnable during demos and local development.
"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

preferred_url = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = preferred_url or "sqlite:///./aivoa_complaints.db"

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True)
else:
    try:
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        DATABASE_URL = "sqlite:///./aivoa_complaints.db"
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
