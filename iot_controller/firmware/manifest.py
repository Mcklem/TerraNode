import ipaddress
import re
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


ParameterType = Literal[
    "string",
    "password",
    "secret",
    "ip",
    "port",
    "number",
    "boolean",
    "select",
    "pin",
    "interval",
]


class BoardProfile(BaseModel):
    fqbn: str
    name: Optional[str] = None
    architecture: Optional[str] = "esp8266"
    flash_size: Optional[str] = "4M"


class ParameterOption(BaseModel):
    value: Union[str, int, float]
    label: str


class FirmwareParameter(BaseModel):
    id: str
    label: str
    type: ParameterType
    required: bool = True
    default: Optional[Any] = None
    sensitive: bool = False
    description: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    options: Optional[List[ParameterOption]] = None
    validation_regex: Optional[str] = None


class Dependency(BaseModel):
    name: str
    version: Optional[str] = None


class BuildOptions(BaseModel):
    optimize: bool = True
    cpu_freq: Optional[int] = None
    flash_mode: Optional[str] = None


class FirmwareManifest(BaseModel):
    id: str
    name: str
    description: str
    version: str
    category: str = "firmata"
    author: Optional[str] = None
    board: BoardProfile
    upload_methods: List[str] = Field(
        default_factory=lambda: ["web_serial", "binary_download", "source_download"]
    )
    parameters: List[FirmwareParameter] = Field(default_factory=list)
    dependencies: List[Dependency] = Field(default_factory=list)
    build: BuildOptions = Field(default_factory=BuildOptions)


def validate_parameter_value(param: FirmwareParameter, raw_value: Any) -> Any:
    """Validates and coerces a single parameter value according to its definition."""
    # Check if empty or missing
    if raw_value is None or raw_value == "":
        if param.required:
            if param.default is not None:
                raw_value = param.default
            else:
                raise ValueError(f"El parámetro '{param.label}' ({param.id}) es obligatorio.")
        else:
            return param.default

    param_type = param.type

    if param_type in ("string", "password", "secret"):
        val_str = str(raw_value).strip()
        if param.min_length is not None and len(val_str) < param.min_length:
            raise ValueError(
                f"'{param.label}' debe tener al menos {param.min_length} caracteres."
            )
        if param.max_length is not None and len(val_str) > param.max_length:
            raise ValueError(
                f"'{param.label}' no puede exceder {param.max_length} caracteres."
            )
        if param.validation_regex:
            if not re.match(param.validation_regex, val_str):
                raise ValueError(f"'{param.label}' no cumple con el formato requerido.")
        return val_str

    elif param_type == "ip":
        val_str = str(raw_value).strip()
        try:
            ipaddress.IPv4Address(val_str)
            return val_str
        except ipaddress.AddressValueError:
            raise ValueError(f"'{param.label}' ({val_str}) no es una dirección IPv4 válida.")

    elif param_type == "port":
        try:
            val_int = int(raw_value)
            if not (1 <= val_int <= 65535):
                raise ValueError()
            return val_int
        except (ValueError, TypeError):
            raise ValueError(f"'{param.label}' debe ser un puerto de red válido entre 1 y 65535.")

    elif param_type in ("number", "interval"):
        try:
            val_num = float(raw_value) if "." in str(raw_value) else int(raw_value)
            if param.min is not None and val_num < param.min:
                raise ValueError(f"'{param.label}' debe ser mayor o igual a {param.min}.")
            if param.max is not None and val_num > param.max:
                raise ValueError(f"'{param.label}' no puede superar {param.max}.")
            return val_num
        except (ValueError, TypeError) as e:
            if str(e):
                raise
            raise ValueError(f"'{param.label}' debe ser un valor numérico válido.")

    elif param_type == "boolean":
        if isinstance(raw_value, bool):
            return raw_value
        val_str = str(raw_value).lower().strip()
        if val_str in ("true", "1", "yes", "on"):
            return True
        elif val_str in ("false", "0", "no", "off"):
            return False
        raise ValueError(f"'{param.label}' debe ser un valor booleano (true/false).")

    elif param_type == "select":
        val_str = str(raw_value).strip()
        if param.options:
            allowed = [str(opt.value) for opt in param.options]
            if val_str not in allowed:
                raise ValueError(
                    f"'{param.label}' contiene un valor inválido '{val_str}'. Opciones: {allowed}."
                )
        return val_str

    elif param_type == "pin":
        val_str = str(raw_value).strip().upper()
        # Common ESP8266 pins: D0-D8, A0, or raw GPIO numbers
        if not re.match(r"^(D[0-8]|A0|GPIO[0-9]{1,2}|[0-9]{1,2})$", val_str):
            raise ValueError(f"'{param.label}' ({val_str}) no es una designación de pin válida.")
        return val_str

    return raw_value


def validate_user_parameters(
    manifest: FirmwareManifest, user_values: Dict[str, Any]
) -> Dict[str, Any]:
    """Validates all user-submitted values against the manifest parameter schema.
    
    Returns a cleaned, validated dictionary with all parameters resolved.
    """
    validated: Dict[str, Any] = {}
    for param in manifest.parameters:
        raw = user_values.get(param.id)
        validated[param.id] = validate_parameter_value(param, raw)
    return validated
