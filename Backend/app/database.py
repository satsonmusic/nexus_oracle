"""
app/database.py — Async PostgreSQL setup via SQLAlchemy
Phase 2: Persistent storage for sessions, dossiers, users, and judge violations.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, DateTime, Text, Integer, Boolean
from sqlalchemy.sql import func
import datetime

# ---------------------------------------------------------------------------
# DATABASE URL
# Railway injects DATABASE_URL automatically when PostgreSQL is added.
# Falls back to SQLite for local dev.
# ---------------------------------------------------------------------------
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./nexus_local.db")

# SQLAlchemy requires postgresql+asyncpg:// not postgres://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# MODELS
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id           = Column(String, primary_key=True)   # Clerk user ID
    email        = Column(String, unique=True, nullable=False)
    name         = Column(String, nullable=True)
    tier         = Column(String, default="free")     # free | pro | enterprise
    created_at   = Column(DateTime, default=func.now())
    last_seen_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Usage tracking
    sovereign_runs_today  = Column(Integer, default=0)
    sovereign_runs_month  = Column(Integer, default=0)
    quick_runs_today      = Column(Integer, default=0)
    usage_reset_date      = Column(DateTime, default=func.now())


class Session(Base):
    __tablename__ = "sessions"

    id           = Column(String, primary_key=True)   # session UUID
    user_id      = Column(String, nullable=True)       # Clerk user ID (null = anonymous)
    task         = Column(Text, nullable=False)
    mode         = Column(String, default="SOVEREIGN") # QUICK | CODE | SOVEREIGN
    status       = Column(String, default="pending")   # pending | running | complete | error
    score        = Column(Float, nullable=True)
    verdict      = Column(String, nullable=True)
    judge_action = Column(String, nullable=True)
    iterations   = Column(Integer, default=0)
    created_at   = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)


class Dossier(Base):
    __tablename__ = "dossiers"

    id         = Column(String, primary_key=True)   # session ID
    user_id    = Column(String, nullable=True)
    task       = Column(Text, nullable=False)
    content    = Column(Text, nullable=False)        # full markdown dossier
    score      = Column(Float, nullable=True)
    verdict    = Column(String, nullable=True)
    created_at = Column(DateTime, default=func.now())
    is_public  = Column(Boolean, default=False)      # shareable URL opt-in


class JudgeViolation(Base):
    __tablename__ = "judge_violations"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False)
    user_id    = Column(String, nullable=True)
    task_type  = Column(String, nullable=True)
    violation_type = Column(String, nullable=False)
    location   = Column(String, nullable=True)
    severity   = Column(String, nullable=True)
    fix        = Column(Text, nullable=True)
    score      = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

async def get_db():
    """Dependency injection for FastAPI routes."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """Create all tables on startup if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[ DATABASE ] Tables ready.")
