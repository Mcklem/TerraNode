from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from api.dependencies import get_config_manager, get_system
from config_manager.models import BackupMetadata, ConfigStatus, DiffResult, ValidationResult
from config_manager.service import (
    ConfigManagerService,
    ConfigurationConflictError,
    ConfigurationSaveError,
)
from config_manager.yaml_parser import normalize_devices, parse_yaml, to_plain_dict
from core.system import ControllerSystem

router = APIRouter(prefix="/api/v1/config", tags=["Configuration"])


class ConfigResponse(BaseModel):
    raw_yaml: str = Field(..., description="Contenido YAML del archivo de configuración")
    config: Dict[str, Any] = Field(..., description="Estructura normalizada de configuración")
    status: Dict[str, Any] = Field(..., description="Estado de sincronización y validación")


class ValidateRequest(BaseModel):
    raw_yaml: Optional[str] = Field(None, description="Cadena YAML a validar")
    config: Optional[Dict[str, Any]] = Field(None, description="Diccionario de configuración a validar")


class DiffRequest(BaseModel):
    proposed_yaml: Optional[str] = Field(None, description="Cadena YAML propuesta para comparar contra la activa")
    visual_model: Optional[Dict[str, Any]] = Field(None, description="Modelo estructurado del editor visual para comparar contra la activa")


class YamlToModelRequest(BaseModel):
    raw_yaml: str = Field(..., description="Cadena YAML a convertir a modelo visual normalizado")


class SaveConfigRequest(BaseModel):
    raw_yaml: Optional[str] = Field(None, description="Contenido YAML directo para guardar")
    visual_model: Optional[Dict[str, Any]] = Field(None, description="Modelo estructurado del editor visual")
    base_checksum: Optional[str] = Field(None, description="Hash SHA-256 de la versión base para detección de conflictos")
    author: Optional[str] = Field("operator", description="Identificador del operador que realiza el cambio")
    description: Optional[str] = Field("Actualización de configuración", description="Descripción del cambio para la auditoría")


class SaveConfigResponse(BaseModel):
    success: bool
    checksum: str
    backup_id: str
    diff: Dict[str, Any]
    env_changes: List[Dict[str, Any]] = Field(default_factory=list)
    message: str


class ApplyConfigRequest(BaseModel):
    force: Optional[bool] = Field(False, description="Forzar recarga aunque existan advertencias")


class ApplyConfigResponse(BaseModel):
    success: bool
    reloaded_at: str
    runtime_checksum: str
    message: str
    report: Dict[str, Any]


class RestoreBackupRequest(BaseModel):
    author: Optional[str] = Field("operator", description="Operador que solicita la restauración")


class RestoreBackupResponse(BaseModel):
    success: bool
    checksum: str
    pre_restore_backup_id: str
    message: str


@router.get(
    "",
    response_model=ConfigResponse,
    summary="Obtener configuración activa y estado del sistema",
    description="Retorna el contenido YAML crudo, la configuración normalizada y el estado de sincronización entre disco y tiempo de ejecución.",
)
async def get_config(
    masked: bool = Query(True, description="Si es True, oculta claves secretas (auth_key) con sentinels"),
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    try:
        raw_yaml = config_mgr.read_raw_yaml()
        config_dict = config_mgr.load_active_config(mask=masked)
        status_info = config_mgr.get_status().to_dict()
        return {
            "raw_yaml": raw_yaml,
            "config": config_dict,
            "status": status_info,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer la configuración activa: {e}")


@router.post(
    "/validate",
    response_model=Dict[str, Any],
    summary="Validar configuración en varios niveles",
    description="Ejecuta validación de sintaxis YAML (Nivel 1), estructural (Nivel 2) y semántica/conflictos de pines (Nivel 3).",
)
async def validate_config(
    body: ValidateRequest,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    if body.raw_yaml is not None:
        res = config_mgr.validate(body.raw_yaml)
    elif body.config is not None:
        res = config_mgr.validate(body.config)
    else:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar 'raw_yaml' o 'config' para realizar la validación.",
        )
    return res.to_dict()


@router.post(
    "/diff",
    response_model=Dict[str, Any],
    summary="Generar comparación (diff) contra la configuración guardada",
    description="Compara el YAML o modelo visual propuesto contra la versión activa en disco, ocultando automáticamente contraseñas y claves secretas.",
)
async def get_diff(
    body: DiffRequest,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    if body.proposed_yaml is not None:
        diff = config_mgr.generate_diff(body.proposed_yaml)
        proposed_yaml = body.proposed_yaml
    elif body.visual_model is not None:
        proposed_yaml, diff = config_mgr.generate_diff_for_visual_model(body.visual_model)
    else:
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar 'proposed_yaml' o 'visual_model' para generar el diff.",
        )
    res = diff.to_dict()
    res["proposed_yaml"] = proposed_yaml
    return res


@router.post(
    "/yaml-to-model",
    response_model=Dict[str, Any],
    summary="Convertir YAML a modelo visual normalizado",
    description="Parsea la cadena YAML y devuelve la configuración normalizada para el editor visual.",
)
async def convert_yaml_to_model(
    body: YamlToModelRequest,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    parsed, err, _ = parse_yaml(body.raw_yaml)
    if err or parsed is None:
        raise HTTPException(status_code=400, detail=f"Error de sintaxis YAML: {err}")
    plain = to_plain_dict(parsed)
    normalized = normalize_devices(plain)
    return {"config": normalized}


@router.post(
    "/save",
    response_model=SaveConfigResponse,
    summary="Guardar configuración de forma transaccional",
    description="Valida la nueva configuración, detecta conflictos de concurrencia, crea un respaldo automático y reemplaza el archivo atómicamente.",
)
async def save_config(
    body: SaveConfigRequest,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    try:
        if body.raw_yaml is not None:
            success, checksum, backup_meta, diff_res = config_mgr.save_raw_yaml(
                new_yaml_content=body.raw_yaml,
                base_checksum=body.base_checksum,
                author=body.author or "operator",
                description=body.description or "Edición manual de YAML",
            )
        elif body.visual_model is not None:
            success, checksum, backup_meta, diff_res = config_mgr.save_visual_model(
                visual_model=body.visual_model,
                base_checksum=body.base_checksum,
                author=body.author or "operator",
                description=body.description or "Edición desde interfaz visual",
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Debe proporcionar 'raw_yaml' o 'visual_model' para guardar la configuración.",
            )

        env_changes = getattr(diff_res, "env_changes", [])
        msg = "Configuración guardada exitosamente y respaldo creado."
        if env_changes:
            msg += f" ({len(env_changes)} secretos externalizados de forma segura a .env)"

        return {
            "success": success,
            "checksum": checksum,
            "backup_id": backup_meta.id,
            "diff": diff_res.to_dict(),
            "env_changes": env_changes,
            "message": msg,
        }
    except ConfigurationConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ConfigurationSaveError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error inesperado al guardar la configuración: {e}")


@router.post(
    "/apply",
    response_model=ApplyConfigResponse,
    summary="Aplicar la configuración guardada al runtime",
    description="Recarga dinámicamente los subsistemas de hardware (nodos, dispositivos, reglas y programadores) sin reiniciar el servidor web.",
)
async def apply_config(
    body: Optional[ApplyConfigRequest] = None,
    system: Optional[ControllerSystem] = Depends(get_system),
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    # Verify current file is valid before applying
    status_info = config_mgr.get_status()
    if not status_info.validation.valid:
        error_msgs = "; ".join([e.message for e in status_info.validation.errors])
        raise HTTPException(
            status_code=400,
            detail=f"No se puede aplicar una configuración con errores de validación: {error_msgs}",
        )

    if system is None:
        # In standalone mode or test server without ControllerSystem instance
        now_iso = config_mgr.get_status().saved_checksum
        return {
            "success": True,
            "reloaded_at": "simulated",
            "runtime_checksum": status_info.saved_checksum,
            "message": "Configuración aplicada (modo simulación sin sistema activo).",
            "report": {"status": "OK"},
        }

    try:
        report = await system.reload()
        return {
            "success": True,
            "reloaded_at": report["reloaded_at"],
            "runtime_checksum": report["runtime_checksum"],
            "message": "Configuración aplicada con éxito a todos los subsistemas.",
            "report": report,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo durante la recarga de subsistemas: {e}")


@router.get(
    "/backups",
    response_model=List[Dict[str, Any]],
    summary="Listar respaldos históricos de configuración",
    description="Retorna la lista de respaldos disponibles ordenados del más reciente al más antiguo con metadatos de auditoría.",
)
async def list_backups(
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    backups = config_mgr.backup_mgr.list_backups()
    return [b.to_dict() for b in backups]


@router.get(
    "/backups/{backup_id}",
    response_model=Dict[str, Any],
    summary="Inspeccionar un respaldo específico",
    description="Retorna el contenido YAML completo y los metadatos del respaldo seleccionado.",
)
async def get_backup_detail(
    backup_id: str,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    try:
        yaml_content, meta = config_mgr.backup_mgr.get_backup(backup_id)
        return {
            "metadata": meta.to_dict(),
            "raw_yaml": yaml_content,
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Respaldo '{backup_id}' no encontrado.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post(
    "/backups/{backup_id}/restore",
    response_model=RestoreBackupResponse,
    summary="Restaurar (rollback) a una versión anterior",
    description="Valida el respaldo seleccionado, crea una instantánea de recuperación de la configuración actual y restaura el archivo atómicamente.",
)
async def restore_backup(
    backup_id: str,
    body: Optional[RestoreBackupRequest] = None,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    try:
        author = body.author if body and body.author else "operator"
        success, checksum, pre_backup = config_mgr.restore_backup(backup_id, author=author)
        return {
            "success": success,
            "checksum": checksum,
            "pre_restore_backup_id": pre_backup.id,
            "message": f"Configuración restaurada con éxito desde el respaldo '{backup_id}'.",
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Respaldo '{backup_id}' no encontrado.")
    except (ValueError, ConfigurationSaveError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al restaurar respaldo: {e}")


@router.delete(
    "/backups/{backup_id}",
    summary="Eliminar un respaldo obsoleto",
    description="Elimina el respaldo especificado, impidiendo la eliminación si es la única copia de recuperación disponible.",
)
async def delete_backup(
    backup_id: str,
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    try:
        deleted = config_mgr.backup_mgr.delete_backup(backup_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Respaldo '{backup_id}' no encontrado.")
        return {"success": True, "message": f"Respaldo '{backup_id}' eliminado con éxito."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/schema",
    response_model=Dict[str, Any],
    summary="Metadatos de esquema para generación de formularios",
    description="Retorna tipos de dispositivos soportados, controladores, pines válidos, propiedades y comandos para construir formularios dinámicos.",
)
async def get_schema(
    config_mgr: ConfigManagerService = Depends(get_config_manager),
):
    return config_mgr.get_schema_metadata()
