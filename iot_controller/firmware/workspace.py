import os
import re
import shutil
import time
import zipfile
from typing import Optional
from utils.logging import get_logger

UUID_REGEX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class WorkspaceManager:
    """Manages isolated build workspaces for firmware generation and compilation."""

    def __init__(self, base_workspaces_dir: Optional[str] = None):
        if base_workspaces_dir:
            self.base_dir = os.path.abspath(base_workspaces_dir)
        else:
            # Default to iot_hardware/firmware/.workspaces relative to iot_controller
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            parent_dir = os.path.dirname(base_dir)
            self.base_dir = os.path.join(
                parent_dir, "iot_hardware", "firmware", ".workspaces"
            )

        self._logger = get_logger("WorkspaceManager")
        os.makedirs(self.base_dir, exist_ok=True)

    def validate_build_id(self, build_id: str) -> None:
        """Validates that build_id is a valid canonical UUID to prevent path traversal."""
        if not build_id or not UUID_REGEX.match(str(build_id).strip()):
            raise ValueError(f"Identificador de build no válido (debe ser UUIDv4): '{build_id}'")

    def get_workspace_dir(self, build_id: str) -> str:
        """Returns the absolute path of the workspace directory for the build."""
        self.validate_build_id(build_id)
        target = os.path.abspath(os.path.join(self.base_dir, f"build_{build_id}"))
        if not target.startswith(os.path.abspath(self.base_dir)):
            raise ValueError(f"Acceso ilegal fuera del directorio base de workspaces: '{build_id}'")
        return target

    def create_workspace(self, build_id: str) -> str:
        """Creates an empty isolated workspace directory for the build."""
        workspace_dir = self.get_workspace_dir(build_id)
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)
        os.makedirs(workspace_dir, exist_ok=True)
        return workspace_dir

    def get_sketch_dir(self, build_id: str, sketch_name: str) -> str:
        """Arduino CLI requires sketches to reside in a folder with matching sketch name.
        
        Example: build_<id>/SecureStandardFirmataWiFi/SecureStandardFirmataWiFi.ino
        """
        sketch_dir = os.path.join(self.get_workspace_dir(build_id), sketch_name)
        os.makedirs(sketch_dir, exist_ok=True)
        return sketch_dir

    def get_primary_ino_file(self, build_id: str) -> Optional[str]:
        """Finds the main .ino file inside the workspace."""
        workspace_dir = self.get_workspace_dir(build_id)
        if not os.path.exists(workspace_dir):
            return None
        for root, _, files in os.walk(workspace_dir):
            for f in files:
                if f.endswith(".ino"):
                    return os.path.join(root, f)
        return None

    def get_binary_path(self, build_id: str) -> Optional[str]:
        """Finds the compiled binary (.bin or .hex) inside the workspace."""
        workspace_dir = self.get_workspace_dir(build_id)
        if not os.path.exists(workspace_dir):
            return None
        for root, _, files in os.walk(workspace_dir):
            for f in files:
                if f.endswith(".bin") or f.endswith(".hex"):
                    return os.path.join(root, f)
        return None

    def create_source_zip(self, build_id: str) -> Optional[str]:
        """Creates a zip archive of the configured source code in the workspace."""
        workspace_dir = self.get_workspace_dir(build_id)
        if not os.path.exists(workspace_dir):
            return None

        zip_path = os.path.join(workspace_dir, f"firmware_{build_id}.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(workspace_dir):
                for f in files:
                    if f.endswith(".zip") or f.endswith(".bin") or f.endswith(".hex"):
                        continue
                    full_path = os.path.join(root, f)
                    arcname = os.path.relpath(full_path, workspace_dir)
                    zipf.write(full_path, arcname)

        return zip_path

    def clean_workspace(self, build_id: str) -> None:
        """Removes the workspace directory for the build."""
        workspace_dir = self.get_workspace_dir(build_id)
        if os.path.exists(workspace_dir):
            shutil.rmtree(workspace_dir, ignore_errors=True)

    def clean_old_workspaces(self, max_age_hours: int = 24) -> None:
        """Removes workspaces older than max_age_hours to prevent disk clutter."""
        now = time.time()
        max_age_secs = max_age_hours * 3600
        if not os.path.exists(self.base_dir):
            return

        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            if os.path.isdir(item_path) and item.startswith("build_"):
                try:
                    stat = os.stat(item_path)
                    if now - stat.st_mtime > max_age_secs:
                        shutil.rmtree(item_path, ignore_errors=True)
                        self._logger.debug(f"Cleaned expired workspace: {item}")
                except Exception as e:
                    self._logger.warning(f"Error cleaning workspace {item}: {e}")
