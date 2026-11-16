import json
import time
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import desc, func, select
from storage.database import Database, FirmwareBuildModel
from utils.logging import get_logger


class FirmwareRepository:
    """Manages persistence of firmware build records in controller.db."""

    def __init__(self, database: Database):
        self.db = database
        self._logger = get_logger("FirmwareRepository")

    async def create_build(
        self,
        build_id: str,
        template_id: str,
        template_version: str,
        target_fqbn: str,
        public_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Creates a new build record in QUEUED status."""
        now = time.time()
        params_json = json.dumps(public_params) if public_params else None

        def _insert(session):
            record = FirmwareBuildModel(
                id=build_id,
                timestamp=now,
                template_id=template_id,
                template_version=template_version,
                target_fqbn=target_fqbn,
                status="QUEUED",
                status_message="Build inicializado y código fuente generado.",
                public_params_json=params_json,
            )
            session.add(record)
            return self._record_to_dict(record)

        return await self.db.run_in_session(_insert)

    async def update_status(
        self,
        build_id: str,
        status: str,
        status_message: Optional[str] = None,
        compiler_output: Optional[str] = None,
        binary_filename: Optional[str] = None,
        binary_size_bytes: Optional[int] = None,
        checksum_sha256: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Updates the status and metadata of an existing build."""
        now = time.time()

        def _update(session):
            stmt = select(FirmwareBuildModel).where(FirmwareBuildModel.id == build_id)
            record = session.scalar(stmt)
            if not record:
                return None

            record.status = status
            if status_message is not None:
                record.status_message = status_message
            if compiler_output is not None:
                record.compiler_output = compiler_output
            if binary_filename is not None:
                record.binary_filename = binary_filename
            if binary_size_bytes is not None:
                record.binary_size_bytes = binary_size_bytes
            if checksum_sha256 is not None:
                record.checksum_sha256 = checksum_sha256

            if status in ("COMPILED", "FAILED", "FLASHED"):
                record.completed_at = now

            return self._record_to_dict(record)

        return await self.db.run_in_session(_update)

    async def get_build(self, build_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single build record by ID."""
        def _get(session):
            stmt = select(FirmwareBuildModel).where(FirmwareBuildModel.id == build_id)
            record = session.scalar(stmt)
            return self._record_to_dict(record) if record else None

        return await self.db.run_in_session(_get)

    async def list_builds(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Lists build history ordered by timestamp descending with pagination."""
        def _list(session):
            count_stmt = select(func.count(FirmwareBuildModel.id))
            total = session.scalar(count_stmt) or 0

            stmt = (
                select(FirmwareBuildModel)
                .order_by(desc(FirmwareBuildModel.timestamp))
                .offset(offset)
                .limit(limit)
            )
            records = session.scalars(stmt).all()
            return total, [self._record_to_dict(r) for r in records]

        return await self.db.run_in_session(_list)

    @staticmethod
    def _record_to_dict(record: FirmwareBuildModel) -> Dict[str, Any]:
        params = {}
        if record.public_params_json:
            try:
                params = json.loads(record.public_params_json)
            except Exception:
                pass

        return {
            "id": record.id,
            "timestamp": record.timestamp,
            "template_id": record.template_id,
            "template_version": record.template_version,
            "target_fqbn": record.target_fqbn,
            "status": record.status,
            "status_message": record.status_message,
            "compiler_output": record.compiler_output,
            "binary_filename": record.binary_filename,
            "binary_size_bytes": record.binary_size_bytes,
            "checksum_sha256": record.checksum_sha256,
            "completed_at": record.completed_at,
            "public_params": params,
        }
