import os
import re
import shutil
from typing import Any, Dict, List, Optional
from utils.logging import get_logger


def sanitize_cpp_string(val: Any) -> str:
    """Escapes special characters in string values to prevent C++ macro/string injection."""
    s = str(val)
    # Replace backslashes first, then quotes, newlines, carriage returns
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "\\r")
    return s


def format_replacement_value(val: Any) -> str:
    """Formats a Python value for text template substitution."""
    if isinstance(val, bool):
        return "1" if val else "0"
    return str(val)


class TemplateEngine:
    """Performs deterministic, secure template substitution and isolated source generation."""

    def __init__(self):
        self._logger = get_logger("TemplateEngine")

    def generate(
        self,
        template_dir: str,
        parameters: Dict[str, Any],
        output_dir: str,
        ignore_files: Optional[List[str]] = None,
    ) -> List[str]:
        """Generates configured source code in output_dir from template_dir and parameters.
        
        Returns the list of generated file paths.
        """
        if not os.path.isdir(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")

        os.makedirs(output_dir, exist_ok=True)
        ignored = set(ignore_files or ["manifest.json", "README.md", ".git"])

        generated_files: List[str] = []

        # Prepare formatted replacement mapping
        replacements: Dict[str, str] = {}
        for key, raw_val in parameters.items():
            if isinstance(raw_val, str):
                replacements[key] = sanitize_cpp_string(raw_val)
            else:
                replacements[key] = format_replacement_value(raw_val)

        for root, dirs, files in os.walk(template_dir):
            # Exclude ignored directories
            dirs[:] = [d for d in dirs if d not in ignored]

            rel_path = os.path.relpath(root, template_dir)
            target_sub_dir = (
                output_dir if rel_path == "." else os.path.join(output_dir, rel_path)
            )
            os.makedirs(target_sub_dir, exist_ok=True)

            for file_name in files:
                if file_name in ignored:
                    continue

                source_file = os.path.join(root, file_name)
                target_file = os.path.join(target_sub_dir, file_name)

                # Process code/text files with placeholder replacement
                ext = os.path.splitext(file_name)[1].lower()
                text_exts = {".ino", ".h", ".cpp", ".c", ".txt", ".json", ".properties"}

                if ext in text_exts:
                    with open(source_file, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()

                    # Replace all {{PARAM_ID}} placeholders
                    for param_id, replacement in replacements.items():
                        placeholder = f"{{{{{param_id}}}}}"
                        content = content.replace(placeholder, replacement)

                    # Verify no leftover mandatory placeholders
                    leftover_matches = re.findall(r"\{\{([A-Z0-9_]+)\}\}", content)
                    if leftover_matches:
                        self._logger.warning(
                            f"File '{file_name}' contains unreplaced placeholders: {leftover_matches}"
                        )

                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(content)
                else:
                    # Binary or non-template file: direct copy
                    shutil.copy2(source_file, target_file)

                generated_files.append(target_file)

        self._logger.debug(
            f"Generated {len(generated_files)} configured files into {output_dir}"
        )
        return generated_files
