from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Literal, Optional


class ValidationLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    field: str
    message: str
    level: str = "error"  # 'error', 'warning', 'info'
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationResult:
    valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    infos: List[ValidationIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "infos": [i.to_dict() for i in self.infos],
        }


@dataclass
class BackupMetadata:
    id: str
    filename: str
    timestamp: str
    created_at: float
    author: str
    description: str
    checksum: str
    size_bytes: int
    diff_summary: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DiffResult:
    unified_diff: str
    has_changes: bool
    added_keys: List[str] = field(default_factory=list)
    removed_keys: List[str] = field(default_factory=list)
    modified_keys: List[str] = field(default_factory=list)
    env_changes: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConfigStatus:
    active_config_path: str
    saved_checksum: str
    runtime_checksum: Optional[str]
    is_synchronized: bool
    last_saved_at: Optional[str]
    last_applied_at: Optional[str]
    counts: Dict[str, int]
    validation: ValidationResult

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_config_path": self.active_config_path,
            "saved_checksum": self.saved_checksum,
            "runtime_checksum": self.runtime_checksum,
            "is_synchronized": self.is_synchronized,
            "last_saved_at": self.last_saved_at,
            "last_applied_at": self.last_applied_at,
            "counts": self.counts,
            "validation": self.validation.to_dict(),
        }
