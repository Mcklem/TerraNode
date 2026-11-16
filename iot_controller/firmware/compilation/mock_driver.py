import hashlib
import os
from typing import List, Optional
from firmware.compilation.base import BaseCompilerDriver, BuildResult
from firmware.manifest import FirmwareManifest
from utils.logging import get_logger


class MockCompilerDriver(BaseCompilerDriver):
    """Simulated compiler driver for testing and systems without Arduino CLI installed."""

    def __init__(self):
        self._logger = get_logger("MockCompilerDriver")

    async def compile(
        self,
        workspace_dir: str,
        sketch_path: str,
        manifest: FirmwareManifest,
        secrets_to_redact: Optional[List[str]] = None,
    ) -> BuildResult:
        self._logger.info(
            f"Simulating firmware compilation for '{manifest.id}' (FQBN: {manifest.board.fqbn})..."
        )

        sketch_name = os.path.splitext(os.path.basename(sketch_path))[0]
        binary_filename = f"{sketch_name}.ino.bin"
        binary_path = os.path.join(workspace_dir, binary_filename)

        # Generate a realistic mock firmware binary (simulating ESP8266 flash image)
        mock_payload = (
            f"TERRANODE_FIRMWARE_HEADER\n"
            f"TEMPLATE_ID={manifest.id}\n"
            f"VERSION={manifest.version}\n"
            f"BOARD={manifest.board.fqbn}\n"
            f"FLASH_SIZE={manifest.board.flash_size}\n"
            f"TIMESTAMP={sketch_name}\n"
        ).encode("utf-8") + (b"\xEA\x04\x00\x00" * 256)

        with open(binary_path, "wb") as f:
            f.write(mock_payload)

        file_size = len(mock_payload)
        sha256 = hashlib.sha256(mock_payload).hexdigest()

        compiler_output = (
            f"Using board '{manifest.board.fqbn}' from core: esp8266:esp8266 (simulated)\n"
            f"Compiling sketch: {sketch_path}\n"
            f"Archiving built core (caching) in C:\\Temp\\arduino-core-cache\n"
            f"Linking everything together...\n"
            f"Executable segment sizes:\n"
            f"IROM   : 231508 bytes (74% flash)\n"
            f"IRAM   : 26844 bytes (81% RAM)\n"
            f"DATA   : 1256 bytes\n"
            f"RODATA : 1804 bytes\n"
            f"BSS    : 28400 bytes\n"
            f"Generated binary: {binary_filename} ({file_size} bytes)\n"
            f"SHA256: {sha256}\n"
            f"Compilación completada exitosamente en modo simulación."
        )

        return BuildResult(
            success=True,
            compiler_output=compiler_output,
            binary_path=binary_path,
            binary_filename=binary_filename,
            binary_size_bytes=file_size,
            checksum_sha256=sha256,
        )
