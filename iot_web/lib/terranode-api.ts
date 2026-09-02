import { z } from 'zod'
import {
  Device,
  DeviceSchema,
  DeviceState,
  Health,
  HealthSchema,
  NodeInfoSchema,
  Override,
  OverrideSchema,
  TerraNode,
  type Mode,
  type DeviceStatus,
  type NodeStatus,
  type CommandPayload,
  type CommandResult,
  type RawPinPayload,
} from './schemas'

export type { Mode, DeviceStatus, NodeStatus, TerraNode, DeviceState, Device, Health, Override, CommandPayload, CommandResult, RawPinPayload }

export const apiFetch = async <T>(
  path: string,
  schema?: z.ZodType<T>,
  init?: RequestInit
): Promise<T> => {
  const url = `/api/terranode${path}`
  const response = await fetch(url, {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })

  let body: any
  try {
    body = await response.json()
  } catch {
    body = { detail: `Respuesta no válida del controlador (${response.status})` }
  }

  if (!response.ok) {
    const errorMsg = body?.detail || body?.message || `Error del controlador (${response.status})`
    throw new Error(errorMsg)
  }

  if (schema) {
    const parseResult = schema.safeParse(body)
    if (!parseResult.success) {
      console.warn(`[TerraNode API] Advertencia de validación de esquema en ${path}:`, parseResult.error.format())
      return body as T
    }
    return parseResult.data
  }

  return body as T
}

export const fetchHealth = (signal?: AbortSignal) =>
  apiFetch<Health>('/health', HealthSchema, { signal })

export const fetchNodes = (signal?: AbortSignal) =>
  apiFetch<TerraNode[]>('/nodes', z.array(NodeInfoSchema), { signal })

export const fetchDevices = (signal?: AbortSignal) =>
  apiFetch<Device[]>('/devices', z.array(DeviceSchema), { signal })

export const fetchOverrides = (signal?: AbortSignal) =>
  apiFetch<Override[]>('/overrides', z.array(OverrideSchema), { signal })

export const deviceValue = (device: Device): string => {
  const state = device.current_state
  if (device.type === 'relay') {
    return state.state ?? '—'
  }
  if (device.type === 'servo') {
    return state.angle == null ? '—' : `${state.angle}°`
  }
  if (device.type === 'soil_moisture') {
    if (state.moisture_percent != null) return `${state.moisture_percent.toFixed(1)}%`
    if (state.value != null) return `${state.value.toFixed(1)}%`
    return '—'
  }
  if (device.type === 'bmp180') {
    if (state.temperature != null) return `${state.temperature.toFixed(1)}°C`
    if (state.value != null) return `${state.value.toFixed(1)}°C`
    return '—'
  }
  if (device.type === 'ldr') {
    const raw = state.raw_value ?? state.value
    return raw == null ? '—' : `${raw} raw`
  }
  const genericVal = state.value ?? state.raw_value
  return genericVal == null ? '—' : String(genericVal)
}

export const getDeviceMetrics = (device: Device): Array<{ label: string; value: string }> => {
  const state = device.current_state
  const metrics: Array<{ label: string; value: string }> = []

  if (device.type === 'bmp180') {
    if (state.pressure != null) {
      metrics.push({ label: 'PRESIÓN', value: `${state.pressure.toFixed(1)} hPa` })
    }
    if (state.altitude != null) {
      metrics.push({ label: 'ALTITUD', value: `${state.altitude.toFixed(0)} m` })
    }
  } else if (device.type === 'soil_moisture') {
    if (state.raw_value != null) {
      metrics.push({ label: 'RAW', value: String(state.raw_value) })
    }
  } else if (device.type === 'ldr') {
    if (state.raw_value != null) {
      metrics.push({ label: 'RAW ADC', value: String(state.raw_value) })
    }
  }

  return metrics
}

export const deviceAction = (device: Device): string => {
  if (device.type === 'relay') {
    return device.current_state.state === 'ON' ? 'turn_off' : 'turn_on'
  }
  return 'set_position'
}
