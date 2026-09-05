"""
Database session / engine setup.

Works with a local Postgres instance or a Supabase Postgres connection
string. Falls back to SQLite for zero-config local development (e.g. when
a contributor just wants to run the API without spinning up Postgres).
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./signalwatch.db")

# SQLite needs this connect_arg when used across threads (FastAPI's
# dependency system may hand a session to a different thread than the
# one that created it).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create tables if they don't exist. Called on app startup.

    For a production deploy you'd normally use Alembic migrations instead
    of create_all, but for a hackathon-scale project this keeps setup to
    a single command.
    """
    from models import models  # noqa: F401  (ensures models are registered)
    Base.metadata.create_all(bind=engine)
