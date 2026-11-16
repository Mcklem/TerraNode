import hashlib
import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from config_manager.models import BackupMetadata
from config_manager.validator import ConfigValidator


class BackupManager:
    """Manages creation, retention, inspection, and safe rollback of configuration backups."""

    def __init__(self, backups_dir: str):
        self.backups_dir = os.path.abspath(backups_dir)
        os.makedirs(self.backups_dir, exist_ok=True)

    def _sanitize_id(self, backup_id: str) -> str:
        """Sanitize backup ID to prevent path traversal."""
        clean = os.path.basename(backup_id.strip())
        if not re.match(r"^system_\d{8}_\d{6}_[a-zA-Z0-9]+$", clean.replace(".yaml", "").replace(".json", "")):
            raise ValueError(f"Invalid or unsafe backup identifier: '{backup_id}'")
        return clean.replace(".yaml", "").replace(".json", "")

    def create_backup(
        self,
        yaml_content: str,
        author: str = "operator",
        description: str = "Configuration update",
        diff_summary: Optional[Dict[str, Any]] = None,
    ) -> BackupMetadata:
        """Save a new backup YAML with associated JSON metadata."""
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        checksum = hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()
        short_hash = checksum[:8]

        backup_id = f"system_{timestamp_str}_{short_hash}"
        yaml_filename = f"{backup_id}.yaml"
        json_filename = f"{backup_id}.json"

        yaml_path = os.path.join(self.backups_dir, yaml_filename)
        json_path = os.path.join(self.backups_dir, json_filename)

        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        meta = BackupMetadata(
            id=backup_id,
            filename=yaml_filename,
            timestamp=now.isoformat(),
            created_at=time.time(),
            author=author,
            description=description,
            checksum=checksum,
            size_bytes=len(yaml_content.encode("utf-8")),
            diff_summary=diff_summary,
        )

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta.to_dict(), f, indent=2)

        return meta

    def list_backups(self) -> List[BackupMetadata]:
        """List all available backups sorted by newest first."""
        results: List[BackupMetadata] = []
        if not os.path.exists(self.backups_dir):
            return results

        for fname in os.listdir(self.backups_dir):
            if fname.endswith(".json"):
                json_path = os.path.join(self.backups_dir, fname)
                try:
                    with open(json_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        meta = BackupMetadata(
                            id=data["id"],
                            filename=data["filename"],
                            timestamp=data.get("timestamp", ""),
                            created_at=data.get("created_at", 0.0),
                            author=data.get("author", "operator"),
                            description=data.get("description", ""),
                            checksum=data.get("checksum", ""),
                            size_bytes=data.get("size_bytes", 0),
                            diff_summary=data.get("diff_summary"),
                        )
                        results.append(meta)
                except Exception:
                    continue

        # Sort descending by created_at
        results.sort(key=lambda b: b.created_at, reverse=True)
        return results

    def get_backup(self, backup_id: str) -> Tuple[str, BackupMetadata]:
        """Load backup YAML content and metadata."""
        clean_id = self._sanitize_id(backup_id)
        yaml_path = os.path.join(self.backups_dir, f"{clean_id}.yaml")
        json_path = os.path.join(self.backups_dir, f"{clean_id}.json")

        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Backup file not found for ID: {clean_id}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()

        meta: BackupMetadata
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                d = json.load(f)
                meta = BackupMetadata(**d)
        else:
            chk = hashlib.sha256(yaml_content.encode("utf-8")).hexdigest()
            meta = BackupMetadata(
                id=clean_id,
                filename=f"{clean_id}.yaml",
                timestamp=datetime.now().isoformat(),
                created_at=os.path.getmtime(yaml_path),
                author="unknown",
                description="Recovered backup",
                checksum=chk,
                size_bytes=len(yaml_content.encode("utf-8")),
            )

        return yaml_content, meta

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup, ensuring at least one backup remains."""
        backups = self.list_backups()
        if len(backups) <= 1:
            raise ValueError("Cannot delete the only available configuration backup.")

        clean_id = self._sanitize_id(backup_id)
        yaml_path = os.path.join(self.backups_dir, f"{clean_id}.yaml")
        json_path = os.path.join(self.backups_dir, f"{clean_id}.json")

        deleted = False
        if os.path.exists(yaml_path):
            os.remove(yaml_path)
            deleted = True
        if os.path.exists(json_path):
            os.remove(json_path)

        return deleted
