import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from api.dependencies import get_firmware_service
from firmware.service import FirmwareService

router = APIRouter(prefix="/api/v1/firmware", tags=["Firmware Studio"])


class ConfigurationPayload(BaseModel):
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Diccionario de valores configurados para la plantilla de firmware.",
    )


class CompilePayload(BaseModel):
    force_mock: bool = Field(
        default=False,
        description="Fuerza el uso del driver simulador en lugar del compilador real.",
    )


@router.get("/templates", summary="Listar catálogo de plantillas de firmware")
async def list_templates(
    service: FirmwareService = Depends(get_firmware_service),
) -> List[Dict[str, Any]]:
    """Devuelve la lista de plantillas de firmware disponibles en el catálogo."""
    manifests = service.list_templates()
    return [m.model_dump() for m in manifests]


@router.get("/templates/{template_id}", summary="Detalles y documentación de plantilla")
async def get_template_details(
    template_id: str,
    service: FirmwareService = Depends(get_firmware_service),
) -> Dict[str, Any]:
    """Devuelve el manifiesto completo y documentación README de la plantilla especificada."""
    details = service.get_template(template_id)
    if not details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plantilla de firmware no encontrada: '{template_id}'",
        )
    return details


@router.post("/templates/{template_id}/validate", summary="Validar configuración de plantilla")
async def validate_template_config(
    template_id: str,
    payload: ConfigurationPayload,
    service: FirmwareService = Depends(get_firmware_service),
) -> Dict[str, Any]:
    """Valida los parámetros de configuración enviados por el usuario frente al esquema del manifiesto."""
    try:
        validated = service.validate_config(template_id, payload.parameters)
        return {
            "valid": True,
            "template_id": template_id,
            "parameters": validated,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.post("/templates/{template_id}/generate", summary="Generar código fuente configurado")
async def generate_configured_firmware(
    template_id: str,
    payload: ConfigurationPayload,
    service: FirmwareService = Depends(get_firmware_service),
) -> Dict[str, Any]:
    """Genera el código fuente personalizado en un espacio de trabajo aislado y registra el build."""
    try:
        build_record = await service.generate_build(template_id, payload.parameters)
        return build_record
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al generar código: {e}",
        )


@router.post("/builds/{build_id}/compile", summary="Compilar firmware generado")
async def compile_firmware_build(
    build_id: str,
    payload: Optional[CompilePayload] = None,
    service: FirmwareService = Depends(get_firmware_service),
) -> Dict[str, Any]:
    """Inicia la compilación del firmware en el espacio de trabajo generado."""
    try:
        driver_override = None
        if payload and payload.force_mock:
            from firmware.compilation.mock_driver import MockCompilerDriver
            driver_override = MockCompilerDriver()

        result = await service.compile_build(build_id, driver_override=driver_override)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante la compilación: {e}",
        )


@router.get("/builds/{build_id}", summary="Estado y metadatos de build")
async def get_build_status(
    build_id: str,
    service: FirmwareService = Depends(get_firmware_service),
) -> Dict[str, Any]:
    """Consulta el estado del build, porcentaje y salida de compilación redactada."""
    record = await service.get_build(build_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build no encontrado: '{build_id}'",
        )
    return record


@router.get("/builds/{build_id}/binary", summary="Descargar binario compilado (.bin)")
async def download_firmware_binary(
    build_id: str,
    service: FirmwareService = Depends(get_firmware_service),
):
    """Descarga el archivo binario compilado listo para flasheo externo o Web Serial."""
    binary_path = service.get_binary_path(build_id)
    if not binary_path or not os.path.isfile(binary_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Binario compilado no encontrado para este build. Compila primero el firmware.",
        )
    filename = os.path.basename(binary_path)
    return FileResponse(
        binary_path,
        media_type="application/octet-stream",
        filename=filename,
    )


@router.get("/builds/{build_id}/source", summary="Descargar código fuente configurado (.zip)")
async def download_firmware_source(
    build_id: str,
    service: FirmwareService = Depends(get_firmware_service),
):
    """Descarga el código fuente C++ configurado con todas las variables sustituidas en un archivo .zip."""
    zip_path = service.get_source_zip(build_id)
    if not zip_path or not os.path.isfile(zip_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Espacio de trabajo o fuentes no disponibles para descarga.",
        )
    filename = os.path.basename(zip_path)
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=filename,
    )


@router.get("/history", summary="Historial de compilaciones")
async def list_firmware_history(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: FirmwareService = Depends(get_firmware_service),
) -> Dict[str, Any]:
    """Lista las compilaciones anteriores registradas en controller.db."""
    total, builds = await service.list_history(limit=limit, offset=offset)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "builds": builds,
    }
