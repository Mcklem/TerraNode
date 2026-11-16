import os
import uuid
from typing import Any, Dict, List, Optional, Tuple
from firmware.catalog import FirmwareCatalog
from firmware.compilation.arduino_cli import ArduinoCliDriver
from firmware.compilation.base import BaseCompilerDriver
from firmware.compilation.mock_driver import MockCompilerDriver
from firmware.engine import TemplateEngine
from firmware.manifest import FirmwareManifest, validate_user_parameters
from firmware.repository import FirmwareRepository
from firmware.workspace import WorkspaceManager
from storage.database import Database
from utils.logging import get_logger


class FirmwareService:
    """Unified service layer orchestrating firmware catalog, generation, compilation, and storage."""

    def __init__(
        self,
        database: Optional[Database] = None,
        templates_dir: Optional[str] = None,
        workspaces_dir: Optional[str] = None,
        compiler_driver: Optional[BaseCompilerDriver] = None,
    ):
        self._logger = get_logger("FirmwareService")
        self.catalog = FirmwareCatalog(templates_dir)
        self.engine = TemplateEngine()
        self.workspace_mgr = WorkspaceManager(workspaces_dir)

        # Database and repository
        self.db = database or Database()
        self.repo = FirmwareRepository(self.db)

        # In-memory store for sensitive parameters during build lifecycle
        self._active_build_secrets: Dict[str, List[str]] = {}

        # Default compiler driver: Arduino CLI if installed, otherwise Mock driver
        if compiler_driver:
            self.compiler = compiler_driver
        else:
            cli_driver = ArduinoCliDriver()
            if cli_driver.is_available():
                self.compiler = cli_driver
                self._logger.info("FirmwareService using local ArduinoCliDriver.")
            else:
                self.compiler = MockCompilerDriver()
                self._logger.info(
                    "arduino-cli not detected; FirmwareService using MockCompilerDriver."
                )

    def list_templates(self) -> List[FirmwareManifest]:
        """Returns all discovered templates."""
        return self.catalog.list_manifests()

    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Returns template manifest and README documentation."""
        manifest = self.catalog.get_manifest(template_id)
        if not manifest:
            return None
        readme = self.catalog.get_readme(template_id)
        data = manifest.model_dump()
        data["readme"] = readme
        return data

    def validate_config(
        self, template_id: str, raw_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validates configuration parameters against the manifest."""
        manifest = self.catalog.get_manifest(template_id)
        if not manifest:
            raise ValueError(f"Plantilla de firmware no encontrada: '{template_id}'")
        return validate_user_parameters(manifest, raw_params)

    async def generate_build(
        self, template_id: str, raw_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validates inputs, creates an isolated workspace, and generates configured source code."""
        manifest = self.catalog.get_manifest(template_id)
        if not manifest:
            raise ValueError(f"Plantilla de firmware no encontrada: '{template_id}'")

        template_dir = self.catalog.get_template_dir(template_id)
        if not template_dir:
            raise FileNotFoundError(f"Directorio de plantilla no encontrado para '{template_id}'")

        # 1. Validate parameters
        validated_params = validate_user_parameters(manifest, raw_params)

        # 2. Extract public params (excluding sensitive/passwords) for database audit
        sensitive_ids = {p.id for p in manifest.parameters if p.sensitive or p.type in ("password", "secret")}
        public_params = {k: v for k, v in validated_params.items() if k not in sensitive_ids}
        secrets_list = [str(v) for k, v in validated_params.items() if k in sensitive_ids]

        # 3. Create build ID and isolate workspace
        build_id = str(uuid.uuid4())
        workspace_dir = self.workspace_mgr.create_workspace(build_id)

        # Store secrets in memory for the active compilation lifecycle
        self._active_build_secrets[build_id] = secrets_list

        # 4. Generate configured source files
        try:
            generated_files = self.engine.generate(
                template_dir=template_dir,
                parameters=validated_params,
                output_dir=workspace_dir,
            )

            # 5. Persist record in database
            build_record = await self.repo.create_build(
                build_id=build_id,
                template_id=template_id,
                template_version=manifest.version,
                target_fqbn=manifest.board.fqbn,
                public_params=public_params,
            )

            build_record["generated_files_count"] = len(generated_files)
            return build_record

        except Exception as e:
            self.workspace_mgr.clean_workspace(build_id)
            self._logger.error(f"Error generating build {build_id}: {e}")
            raise

    async def compile_build(
        self, build_id: str, driver_override: Optional[BaseCompilerDriver] = None
    ) -> Dict[str, Any]:
        """Executes compilation for an existing generated build workspace."""
        build_record = await self.repo.get_build(build_id)
        if not build_record:
            raise ValueError(f"Build ID '{build_id}' no encontrado.")

        manifest = self.catalog.get_manifest(build_record["template_id"])
        if not manifest:
            raise ValueError(f"Plantilla '{build_record['template_id']}' ya no existe en el catálogo.")

        workspace_dir = self.workspace_mgr.get_workspace_dir(build_id)
        sketch_path = self.workspace_mgr.get_primary_ino_file(build_id)
        if not sketch_path:
            raise FileNotFoundError(f"Archivo .ino no encontrado en el espacio de trabajo de {build_id}.")

        # Update status to COMPILING
        await self.repo.update_status(
            build_id=build_id,
            status="COMPILING",
            status_message="Compilando firmware con el toolchain de Arduino...",
        )

        compiler = driver_override or self.compiler
        secrets_to_redact = self._active_build_secrets.get(build_id, [])

        try:
            result = await compiler.compile(
                workspace_dir=workspace_dir,
                sketch_path=sketch_path,
                manifest=manifest,
                secrets_to_redact=secrets_to_redact,
            )

            if result.success:
                updated = await self.repo.update_status(
                    build_id=build_id,
                    status="COMPILED",
                    status_message="Compilación completada exitosamente. Binario listo para flasheo.",
                    compiler_output=result.compiler_output,
                    binary_filename=result.binary_filename,
                    binary_size_bytes=result.binary_size_bytes,
                    checksum_sha256=result.checksum_sha256,
                )
            else:
                updated = await self.repo.update_status(
                    build_id=build_id,
                    status="FAILED",
                    status_message=f"Error durante la compilación: {result.error}",
                    compiler_output=result.compiler_output,
                )

            # Clean memory secrets
            self._active_build_secrets.pop(build_id, None)
            return updated or {}

        except Exception as e:
            self._logger.error(f"Unexpected error compiling build {build_id}: {e}")
            await self.repo.update_status(
                build_id=build_id,
                status="FAILED",
                status_message=f"Excepción inesperada: {e}",
                compiler_output=str(e),
            )
            self._active_build_secrets.pop(build_id, None)
            raise

    async def get_build(self, build_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a build record by ID."""
        return await self.repo.get_build(build_id)

    async def list_history(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """Lists build history from controller.db."""
        return await self.repo.list_builds(limit=limit, offset=offset)

    def get_binary_path(self, build_id: str) -> Optional[str]:
        """Returns path to compiled binary if it exists."""
        return self.workspace_mgr.get_binary_path(build_id)

    def get_source_zip(self, build_id: str) -> Optional[str]:
        """Packages and returns path to the configured source zip."""
        return self.workspace_mgr.create_source_zip(build_id)
