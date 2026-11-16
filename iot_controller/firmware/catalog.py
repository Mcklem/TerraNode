import json
import os
from typing import Dict, List, Optional
from utils.logging import get_logger
from firmware.manifest import FirmwareManifest


class FirmwareCatalog:
    """Discovers, parses, and provides access to registered firmware templates."""

    def __init__(self, templates_dir: Optional[str] = None):
        if templates_dir:
            self.templates_dir = os.path.abspath(templates_dir)
        else:
            # Default to ../iot_hardware/firmware/templates relative to iot_controller
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parent_dir = os.path.dirname(base_dir)
            self.templates_dir = os.path.join(
                parent_dir, "iot_hardware", "firmware", "templates"
            )

        self._logger = get_logger("FirmwareCatalog")
        self._manifests: Dict[str, FirmwareManifest] = {}
        self._template_dirs: Dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Scans the templates directory and reloads all valid manifests."""
        self._manifests.clear()
        self._template_dirs.clear()

        if not os.path.exists(self.templates_dir):
            self._logger.warning(
                f"Templates directory not found: {self.templates_dir}"
            )
            return

        for item in sorted(os.listdir(self.templates_dir)):
            item_path = os.path.join(self.templates_dir, item)
            if not os.path.isdir(item_path):
                continue

            manifest_path = os.path.join(item_path, "manifest.json")
            if not os.path.isfile(manifest_path):
                continue

            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                manifest = FirmwareManifest.model_validate(data)
                self._manifests[manifest.id] = manifest
                self._template_dirs[manifest.id] = item_path
                self._logger.debug(
                    f"Loaded firmware template '{manifest.id}' v{manifest.version}"
                )
            except Exception as e:
                self._logger.error(
                    f"Failed to load manifest from '{manifest_path}': {e}"
                )

        self._logger.info(
            f"Firmware catalog initialized with {len(self._manifests)} templates from {self.templates_dir}"
        )

    def list_manifests(self) -> List[FirmwareManifest]:
        """Returns all loaded firmware manifests."""
        return list(self._manifests.values())

    def get_manifest(self, template_id: str) -> Optional[FirmwareManifest]:
        """Returns the manifest for the requested template ID, or None."""
        return self._manifests.get(template_id)

    def get_template_dir(self, template_id: str) -> Optional[str]:
        """Returns the physical directory of the requested template, or None."""
        return self._template_dirs.get(template_id)

    def get_readme(self, template_id: str) -> Optional[str]:
        """Returns the markdown README documentation of the template if present."""
        tmpl_dir = self.get_template_dir(template_id)
        if not tmpl_dir:
            return None
        readme_path = os.path.join(tmpl_dir, "README.md")
        if os.path.isfile(readme_path):
            try:
                with open(readme_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                return None
        return None
