# app/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base

# Use DATABASE_URL from environment if set, otherwise fall back to SQLite
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./WebApplication.db"   # local development fallback
)

# SQLite needs check_same_thread=False, PostgreSQL does not
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()