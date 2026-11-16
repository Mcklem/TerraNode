import asyncio
import hashlib
import os
import shutil
from typing import List, Optional
from firmware.compilation.base import BaseCompilerDriver, BuildResult
from firmware.manifest import FirmwareManifest
from utils.logging import get_logger


def redact_secrets(text: str, secrets: Optional[List[str]]) -> str:
    """Replaces sensitive string values in compiler logs with [REDACTED]."""
    if not secrets or not text:
        return text
    clean = text
    for secret in secrets:
        if secret and len(secret) >= 4:
            clean = clean.replace(secret, "[REDACTED]")
    return clean


class ArduinoCliDriver(BaseCompilerDriver):
    """Executes firmware compilation using local arduino-cli binary."""

    def __init__(self, cli_path: Optional[str] = None):
        self._logger = get_logger("ArduinoCliDriver")
        self.cli_path = cli_path or shutil.which("arduino-cli")

    def is_available(self) -> bool:
        """Returns True if arduino-cli binary is available on PATH."""
        return bool(self.cli_path and os.path.exists(self.cli_path))

    async def compile(
        self,
        workspace_dir: str,
        sketch_path: str,
        manifest: FirmwareManifest,
        secrets_to_redact: Optional[List[str]] = None,
    ) -> BuildResult:
        if not self.is_available():
            return BuildResult(
                success=False,
                compiler_output="arduino-cli no se encuentra instalado en el sistema.",
                error="ARDUINO_CLI_NOT_FOUND",
            )

        cmd = [
            self.cli_path,
            "compile",
            "--fqbn",
            manifest.board.fqbn,
            "--output-dir",
            workspace_dir,
            sketch_path,
        ]

        self._logger.info(f"Running arduino-cli: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_dir,
            )

            stdout_b, stderr_b = await asyncio.wait_for(
                process.communicate(), timeout=300.0  # 5 min timeout
            )

            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
            combined_output = f"{stdout}\n{stderr}".strip()

            sanitized_output = redact_secrets(combined_output, secrets_to_redact)

            if process.returncode != 0:
                self._logger.error(f"Compilation failed with exit code {process.returncode}")
                return BuildResult(
                    success=False,
                    compiler_output=sanitized_output,
                    error=f"Compilation error (exit code {process.returncode})",
                )

            # Search for generated binary (.bin)
            sketch_base = os.path.splitext(os.path.basename(sketch_path))[0]
            binary_filename = None
            binary_path = None

            for f in os.listdir(workspace_dir):
                if f.endswith(".bin") or f.endswith(".hex"):
                    binary_filename = f
                    binary_path = os.path.join(workspace_dir, f)
                    break

            if not binary_path or not os.path.isfile(binary_path):
                return BuildResult(
                    success=False,
                    compiler_output=sanitized_output,
                    error="El compilador finalizó pero no se encontró el archivo binario generado.",
                )

            with open(binary_path, "rb") as f:
                content = f.read()
            size = len(content)
            sha256 = hashlib.sha256(content).hexdigest()

            return BuildResult(
                success=True,
                compiler_output=sanitized_output,
                binary_path=binary_path,
                binary_filename=binary_filename,
                binary_size_bytes=size,
                checksum_sha256=sha256,
            )

        except asyncio.TimeoutError:
            self._logger.error("Compilation timed out after 300 seconds.")
            return BuildResult(
                success=False,
                compiler_output="Tiempo de compilación agotado (timeout de 300 segundos).",
                error="COMPILATION_TIMEOUT",
            )
        except Exception as e:
            self._logger.error(f"Unexpected compilation failure: {e}")
            return BuildResult(
                success=False,
                compiler_output=f"Error inesperado al ejecutar el compilador: {e}",
                error=str(e),
            )
