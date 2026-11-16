"""TerraNode Firmware Studio Package.

Provides firmware template discovery, parameter validation, isolated workspace generation,
compilation driver abstraction, and build tracking in controller.db.
"""

from firmware.manifest import FirmwareManifest, FirmwareParameter, BoardProfile
from firmware.catalog import FirmwareCatalog
from firmware.engine import TemplateEngine

__all__ = [
    "FirmwareManifest",
    "FirmwareParameter",
    "BoardProfile",
    "FirmwareCatalog",
    "TemplateEngine",
]
