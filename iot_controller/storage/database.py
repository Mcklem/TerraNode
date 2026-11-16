import asyncio
import os
import time
from typing import Any, Dict, List, Optional
from sqlalchemy import Float, Index, Integer, String, Text, create_engine, select, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from core.settings import settings
from utils.logging import get_logger


class Base(DeclarativeBase):
    """SQLAlchemy Declarative Base class."""
    pass


class NodeHistoryModel(Base):
    """Historical append-only record of node connectivity events and IP details."""
    __tablename__ = "node_history"
    __table_args__ = (
        Index("idx_node_hist_node_ts", "node_id", "timestamp"),
    )

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
    __table_args__ = (
        Index("idx_meas_dev_ts", "device_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)


class EventModel(Base):
    """Historical event stream audit log of system events."""
    __tablename__ = "events"
    __table_args__ = (
        Index("idx_evt_topic_ts", "topic", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sender: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)


class ActuatorHistoryModel(Base):
    """Historical record of actuator state changes and commands."""
    __tablename__ = "actuator_history"
    __table_args__ = (
        Index("idx_act_dev_ts", "device_id", "timestamp"),
        Index("idx_act_src_ts", "source", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class ScheduleHistoryModel(Base):
    """Historical record of time scheduler executions, durations, and completions."""
    __tablename__ = "schedule_history"
    __table_args__ = (
        Index("idx_sched_sched_ts", "schedule_id", "timestamp"),
        Index("idx_sched_dev_ts", "device_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    schedule_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # TRIGGERED, COMPLETED, BLOCKED
    duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)       # SUCCESS, BLOCKED, FAILED


class FirmwareBuildModel(Base):
    """Historical and tracking record of firmware compilations and builds."""
    __tablename__ = "firmware_builds"
    __table_args__ = (
        Index("idx_fw_tmpl_ts", "template_id", "timestamp"),
        Index("idx_fw_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID4
    timestamp: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    template_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    template_version: Mapped[str] = mapped_column(String(32), nullable=False)
    target_fqbn: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True)  # QUEUED, GENERATED, COMPILED, FAILED
    status_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    compiler_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    binary_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    binary_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    completed_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    public_params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ActiveOverrideModel(Base):
    """Persistent state of active manual device overrides across controller restarts."""
    __tablename__ = "active_overrides"

    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False)
    last_action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    override_source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    set_at: Mapped[float] = mapped_column(Float, nullable=False)
    expires_at: Mapped[Optional[float]] = mapped_column(Float, nullable=True)


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
            if self.database_url.startswith("sqlite"):
                try:
                    with self.engine.connect() as conn:
                        conn.execute(text("PRAGMA journal_mode=WAL;"))
                        conn.execute(text("PRAGMA synchronous=NORMAL;"))
                        conn.execute(text("PRAGMA busy_timeout=10000;"))
                        conn.commit()
                except Exception as e:
                    self._logger.warning(f"Could not apply SQLite WAL pragmas: {e}")

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _create_tables)
        self._logger.info(f"SQLAlchemy ORM Database initialized at URL: {self.database_url}")

    def get_session(self) -> Session:
        if not self.SessionFactory:
            raise RuntimeError("Database engine not initialized. Call initialize() first.")
        return self.SessionFactory()

    async def run_in_session(self, func, read_only: bool = False) -> Any:
        """Execute a function inside a managed SQLAlchemy ORM session asynchronously."""
        def _wrapper():
            with self.get_session() as session:
                try:
                    result = func(session)
                    if not read_only:
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
