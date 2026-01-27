"""
TuneGenie Database Layer

SQLAlchemy-based database layer for persistent storage with proper
connection management and migration support.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.types import JSON

from .config import get_settings
from .logging_config import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models"""
    pass


# ============================================================================
# Database Models
# ============================================================================

class WorkflowExecutionDB(Base):
    """Persistent storage for workflow execution history"""
    
    __tablename__ = "workflow_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    workflow_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    
    # Serialized data
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    
    # Error handling
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_step: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Context
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    
    # Metrics
    api_calls_count: Mapped[int] = mapped_column(Integer, default=0)
    llm_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserTasteProfileDB(Base):
    """Persistent storage for user taste profiles"""
    
    __tablename__ = "user_taste_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # Profile data (serialized)
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    
    # Summary stats
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserFeedbackDB(Base):
    """User feedback on recommendations for learning"""
    
    __tablename__ = "user_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    track_id: Mapped[str] = mapped_column(String(50), index=True)
    
    # Feedback
    feedback_type: Mapped[str] = mapped_column(String(20))  # "liked", "disliked", "saved", "skipped"
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)  # 1-5 scale
    
    # Context
    workflow_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recommendation_source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CacheEntryDB(Base):
    """General-purpose cache storage"""
    
    __tablename__ = "cache_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    cache_value: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ============================================================================
# Database Management
# ============================================================================

class DatabaseManager:
    """
    Manages database connections and sessions.
    
    Provides both sync and async interfaces for database operations.
    """

    _instance: "DatabaseManager | None" = None
    _engine = None
    _session_factory = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._engine is None:
            self._initialize()

    def _initialize(self) -> None:
        """Initialize database connection"""
        settings = get_settings()
        db_url = settings.database.url

        # Ensure data directory exists for SQLite
        if db_url.startswith("sqlite"):
            db_path = db_url.replace("sqlite:///", "")
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create engine
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self._engine = create_engine(
            db_url,
            echo=settings.database.echo,
            pool_pre_ping=True,
            connect_args=connect_args,
        )

        # Enable foreign keys for SQLite
        if db_url.startswith("sqlite"):
            @event.listens_for(self._engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
        )

        logger.info(f"Database initialized: {db_url.split('/')[-1]}")

    def create_tables(self) -> None:
        """Create all database tables"""
        Base.metadata.create_all(bind=self._engine)
        logger.info("Database tables created/verified")

    def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)"""
        Base.metadata.drop_all(bind=self._engine)
        logger.warning("All database tables dropped")

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope around a series of operations.
        
        Usage:
            with db.session() as session:
                session.add(entity)
                session.commit()
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """Get a new session (caller responsible for closing)"""
        return self._session_factory()

    @property
    def engine(self):
        """Access the SQLAlchemy engine"""
        return self._engine


# ============================================================================
# Repository Classes
# ============================================================================

class WorkflowHistoryRepository:
    """Repository for workflow execution history"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save(self, workflow: dict) -> None:
        """Save a workflow execution record"""
        with self.db.session() as session:
            db_workflow = WorkflowExecutionDB(
                workflow_id=workflow.get("workflow_id"),
                workflow_type=workflow.get("workflow_type"),
                status=workflow.get("status", "pending"),
                started_at=workflow.get("started_at"),
                completed_at=workflow.get("completed_at"),
                duration_ms=workflow.get("duration_ms", 0),
                parameters=workflow.get("parameters", {}),
                result=workflow.get("result", {}),
                steps=workflow.get("steps", []),
                error=workflow.get("error"),
                error_step=workflow.get("error_step"),
                user_id=workflow.get("user_id"),
                request_id=workflow.get("request_id"),
                api_calls_count=workflow.get("api_calls_count", 0),
                llm_tokens_used=workflow.get("llm_tokens_used", 0),
            )
            session.merge(db_workflow)

    def get_by_id(self, workflow_id: str) -> dict | None:
        """Get a workflow by ID"""
        with self.db.session() as session:
            result = session.query(WorkflowExecutionDB).filter_by(workflow_id=workflow_id).first()
            if result:
                return self._to_dict(result)
            return None

    def get_recent(self, limit: int = 50, user_id: str | None = None) -> list[dict]:
        """Get recent workflow executions"""
        with self.db.session() as session:
            query = session.query(WorkflowExecutionDB)
            if user_id:
                query = query.filter_by(user_id=user_id)
            results = query.order_by(WorkflowExecutionDB.created_at.desc()).limit(limit).all()
            return [self._to_dict(r) for r in results]

    def get_by_type(self, workflow_type: str, limit: int = 50) -> list[dict]:
        """Get workflows by type"""
        with self.db.session() as session:
            results = (
                session.query(WorkflowExecutionDB)
                .filter_by(workflow_type=workflow_type)
                .order_by(WorkflowExecutionDB.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._to_dict(r) for r in results]

    def get_statistics(self) -> dict:
        """Get workflow execution statistics"""
        with self.db.session() as session:
            from sqlalchemy import func

            total = session.query(func.count(WorkflowExecutionDB.id)).scalar()
            by_status = dict(
                session.query(WorkflowExecutionDB.status, func.count(WorkflowExecutionDB.id))
                .group_by(WorkflowExecutionDB.status)
                .all()
            )
            by_type = dict(
                session.query(WorkflowExecutionDB.workflow_type, func.count(WorkflowExecutionDB.id))
                .group_by(WorkflowExecutionDB.workflow_type)
                .all()
            )
            avg_duration = session.query(func.avg(WorkflowExecutionDB.duration_ms)).scalar()

            return {
                "total_executions": total or 0,
                "by_status": by_status,
                "by_type": by_type,
                "avg_duration_ms": float(avg_duration or 0),
            }

    def _to_dict(self, db_obj: WorkflowExecutionDB) -> dict:
        """Convert DB object to dictionary"""
        return {
            "workflow_id": db_obj.workflow_id,
            "workflow_type": db_obj.workflow_type,
            "status": db_obj.status,
            "started_at": db_obj.started_at.isoformat() if db_obj.started_at else None,
            "completed_at": db_obj.completed_at.isoformat() if db_obj.completed_at else None,
            "duration_ms": db_obj.duration_ms,
            "parameters": db_obj.parameters,
            "result": db_obj.result,
            "steps": db_obj.steps,
            "error": db_obj.error,
            "error_step": db_obj.error_step,
            "user_id": db_obj.user_id,
            "request_id": db_obj.request_id,
            "api_calls_count": db_obj.api_calls_count,
            "llm_tokens_used": db_obj.llm_tokens_used,
        }


class TasteProfileRepository:
    """Repository for user taste profiles"""

    def __init__(self, db: DatabaseManager):
        self.db = db

    def save(self, user_id: str, profile: dict) -> None:
        """Save or update a user's taste profile"""
        with self.db.session() as session:
            db_profile = UserTasteProfileDB(
                user_id=user_id,
                profile_data=profile,
                confidence_score=profile.get("confidence_score", 0.0),
            )
            session.merge(db_profile)

    def get(self, user_id: str) -> dict | None:
        """Get a user's taste profile"""
        with self.db.session() as session:
            result = session.query(UserTasteProfileDB).filter_by(user_id=user_id).first()
            if result:
                return result.profile_data
            return None


# ============================================================================
# Global Access Functions
# ============================================================================

_db_manager: DatabaseManager | None = None


def get_db() -> DatabaseManager:
    """Get the global database manager instance"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


def init_database() -> None:
    """Initialize database and create tables"""
    db = get_db()
    db.create_tables()
