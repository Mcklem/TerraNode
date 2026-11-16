from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from firmware.manifest import FirmwareManifest


class BuildResult(BaseModel):
    success: bool
    compiler_output: str
    binary_path: Optional[str] = None
    binary_filename: Optional[str] = None
    binary_size_bytes: Optional[int] = None
    checksum_sha256: Optional[str] = None
    error: Optional[str] = None


class BaseCompilerDriver(ABC):
    """Abstract interface for firmware compilation engines."""

    @abstractmethod
    async def compile(
        self,
        workspace_dir: str,
        sketch_path: str,
        manifest: FirmwareManifest,
        secrets_to_redact: Optional[List[str]] = None,
    ) -> BuildResult:
        """Executes compilation of the sketch within the isolated workspace."""
        pass
