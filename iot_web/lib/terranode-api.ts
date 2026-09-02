export type Mode = 'AUTO' | 'MANUAL_ON' | 'MANUAL_OFF' | 'MANUAL_VALUE'
export type NodeStatus = 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'ERROR'
export type DeviceStatus = 'OK' | 'ERROR' | 'DISCONNECTED'

export type TerraNode = { id: string; connected: boolean; driver: string; host: string; port: number; enabled: boolean; status: NodeStatus }
export type DeviceState = { device_id: string; state?: 'ON' | 'OFF'; raw_value?: number; moisture_percent?: number; angle?: number; timestamp?: number; status: DeviceStatus }
export type Device = { id: string; type: string; node_id: string; status: DeviceStatus; control_mode: Mode; override_active: boolean; current_state: DeviceState }
export type Health = { status: string; total_nodes: number; connected_nodes: number; total_devices: number; report?: { nodes: Record<string, unknown>; devices: Record<string, unknown> } }
export type Override = { device_id: string; mode: Mode; last_action: string; override_source: string; set_at: number; expires_at: number | null }

export const apiFetch = async <T>(path: string, init?: RequestInit): Promise<T> => {
  const response = await fetch(`/api/terranode${path}`, { ...init, headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers } })
  const body = await response.json().catch(() => ({ detail: 'Respuesta inválida del controlador' }))
  if (!response.ok) throw new Error(body.detail || `Error del controlador (${response.status})`)
  return body as T
}

export const deviceValue = (device: Device) => {
  const state = device.current_state
  if (device.type === 'relay') return state.state ?? '—'
  if (device.type === 'servo') return state.angle == null ? '—' : `${state.angle}°`
  if (device.type === 'soil_moisture') return state.moisture_percent == null ? '—' : `${state.moisture_percent.toFixed(1)}%`
  return state.raw_value == null ? '—' : String(state.raw_value)
}

export const deviceAction = (device: Device) => device.type === 'relay' ? (device.current_state.state === 'ON' ? 'turn_off' : 'turn_on') : 'set_position'
