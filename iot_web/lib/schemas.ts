import { z } from 'zod'

export const ControlModeSchema = z.enum(['AUTO', 'MANUAL_ON', 'MANUAL_OFF', 'MANUAL_VALUE'])
export type Mode = z.infer<typeof ControlModeSchema>

export const NodeStatusSchema = z.enum(['CONNECTED', 'DISCONNECTED', 'RECONNECTING', 'ERROR'])
export type NodeStatus = z.infer<typeof NodeStatusSchema>

export const DeviceStatusSchema = z.enum(['OK', 'ERROR', 'DISCONNECTED'])
export type DeviceStatus = z.infer<typeof DeviceStatusSchema>

export const NodeInfoSchema = z.object({
  id: z.string(),
  connected: z.boolean(),
  driver: z.string(),
  host: z.string(),
  port: z.number(),
  enabled: z.boolean(),
  status: NodeStatusSchema,
})
export type TerraNode = z.infer<typeof NodeInfoSchema>

export const DeviceStateSchema = z.object({
  device_id: z.string().optional(),
  state: z.string().optional(),
  raw_value: z.number().optional(),
  value: z.number().optional(),
  moisture_percent: z.number().optional(),
  temperature: z.number().optional(),
  pressure: z.number().optional(),
  altitude: z.number().optional(),
  angle: z.number().optional(),
  timestamp: z.number().optional(),
  status: z.string().optional(),
}).passthrough()
export type DeviceState = z.infer<typeof DeviceStateSchema>

export const DeviceSchema = z.object({
  id: z.string(),
  type: z.string(),
  node_id: z.string(),
  status: DeviceStatusSchema,
  control_mode: ControlModeSchema,
  override_active: z.boolean(),
  current_state: DeviceStateSchema,
})
export type Device = z.infer<typeof DeviceSchema>

export const HealthSchema = z.object({
  status: z.string().optional().default('OK'),
  total_nodes: z.number().optional().default(0),
  connected_nodes: z.number().optional().default(0),
  total_devices: z.number().optional().default(0),
  report: z.record(z.string(), z.unknown()).optional(),
  nodes: z.record(z.string(), z.unknown()).optional(),
  devices: z.record(z.string(), z.unknown()).optional(),
}).passthrough()
export type Health = z.infer<typeof HealthSchema>

export const OverrideSchema = z.object({
  device_id: z.string(),
  mode: ControlModeSchema,
  last_action: z.string().nullable().optional(),
  override_source: z.string().nullable().optional(),
  set_at: z.number(),
  expires_at: z.number().nullable().optional(),
})
export type Override = z.infer<typeof OverrideSchema>

export const CommandPayloadSchema = z.object({
  action: z.string(),
  params: z.record(z.string(), z.unknown()).optional(),
  target_mode: ControlModeSchema.optional(),
  user_id: z.string().optional(),
  ttl_seconds: z.number().nullable().optional(),
})
export type CommandPayload = z.infer<typeof CommandPayloadSchema>

export const CommandResultSchema = z.object({
  success: z.boolean(),
  device_id: z.string(),
  applied_action: z.string(),
  current_mode: ControlModeSchema,
  message: z.string(),
  state_payload: DeviceStateSchema,
})
export type CommandResult = z.infer<typeof CommandResultSchema>

export const RawPinCommandSchema = z.object({
  command_type: z.enum(['digital_write', 'analog_write']),
  pin: z.string(),
  value: z.number(),
})
export type RawPinPayload = z.infer<typeof RawPinCommandSchema>
