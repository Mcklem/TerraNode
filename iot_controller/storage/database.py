import asyncio
import os
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from core.settings import settings
from utils.logging import get_logger


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base class."""
    pass


class NodeHistoryModel(Base):
    """Historical append-only record of node connectivity events and IP details."""
    __tablename__ = "node_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    host: Mapped[str] = mapped_column(String(128), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    driver: Mapped[str] = mapped_column(String(32), nullable=False)
    event: Mapped[str] = mapped_column(String(32), nullable=False)


class MeasurementModel(Base):
    """Historical telemetry series of sensor measurements."""
    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class EventModel(Base):
    """Historical event stream audit log of system events."""
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class ActuatorHistoryModel(Base):
    """Historical record of actuator state changes and commands."""
    __tablename__ = "actuator_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class ScheduleHistoryModel(Base):
    """Historical record of time scheduler executions, durations, and completions."""
    __tablename__ = "schedule_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    schedule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # TRIGGERED, COMPLETED, BLOCKED
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)       # SUCCESS, BLOCKED, FAILED


class Database:
    """Thread-safe SQLAlchemy 2.0 ORM Database connection and schema manager."""

    def __init__(self, database_url: Optional[str] = None):
        url = database_url or settings.database_url

        # Format URL if raw local path is provided
        if not ("://" in url):
            abs_path = os.path.abspath(url).replace("\\", "/")
            self.database_url = f"sqlite:///{abs_path}"
        else:
            self.database_url = url

        self._logger = get_logger("Database")
        self.engine = None
        self.SessionFactory = None

    async def initialize(self) -> None:
        """Initialize SQLAlchemy engine and create database schema tables asynchronously."""
        # For local file SQLite, ensure parent directory exists
        if self.database_url.startswith("sqlite:///") and not self.database_url.startswith("sqlite:///:memory:"):
            db_path = self.database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

        connect_args = {}
        if self.database_url.startswith("sqlite"):
            connect_args = {"timeout": 10.0, "check_same_thread": False}

        self.engine = create_engine(
            self.database_url,
            connect_args=connect_args,
            echo=False,
        )
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)

        def _create_tables():
            Base.metadata.create_all(self.engine)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _create_tables)
        self._logger.info(f"SQLAlchemy ORM Database initialized at URL: {self.database_url}")

    def get_session(self) -> Session:
        if not self.SessionFactory:
            raise RuntimeError("Database engine not initialized. Call initialize() first.")
        return self.SessionFactory()

    async def run_in_session(self, func) -> Any:
        """Execute a function inside a managed SQLAlchemy ORM session asynchronously."""
        def _wrapper():
            with self.get_session() as session:
                try:
                    result = func(session)
                    session.commit()
                    return result
                except Exception:
                    session.rollback()
                    raise

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _wrapper)

    def close(self) -> None:
        """Dispose of the SQLAlchemy engine pool."""
        if self.engine:
            self.engine.dispose()
            self._logger.debug("Disposed SQLAlchemy engine pool.")
