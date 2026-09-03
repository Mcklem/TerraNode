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
  device_id: z.string().nullable().optional(),
  state: z.string().nullable().optional(),
  raw_value: z.number().nullable().optional(),
  value: z.number().nullable().optional(),
  moisture_percent: z.number().nullable().optional(),
  temperature: z.number().nullable().optional(),
  pressure: z.number().nullable().optional(),
  altitude: z.number().nullable().optional(),
  angle: z.number().nullable().optional(),
  timestamp: z.number().nullable().optional(),
  status: z.string().nullable().optional(),
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

/* History Schemas */

export const MeasurementRecordSchema = z.object({
  id: z.number(),
  timestamp: z.number(),
  device_id: z.string(),
  value: z.number().nullable().optional(),
  unit: z.string().nullable().optional(),
  status: z.string(),
})
export type MeasurementRecord = z.infer<typeof MeasurementRecordSchema>

export const PaginatedMeasurementsSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  data: z.array(MeasurementRecordSchema),
})
export type PaginatedMeasurements = z.infer<typeof PaginatedMeasurementsSchema>

export const ActuatorHistoryRecordSchema = z.object({
  id: z.number(),
  timestamp: z.number(),
  device_id: z.string(),
  state: z.string(),
  source: z.string().nullable().optional(),
  user_id: z.string().nullable().optional(),
})
export type ActuatorHistoryRecord = z.infer<typeof ActuatorHistoryRecordSchema>

export const PaginatedActuatorsSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  data: z.array(ActuatorHistoryRecordSchema),
})
export type PaginatedActuators = z.infer<typeof PaginatedActuatorsSchema>

export const NodeHistoryRecordSchema = z.object({
  id: z.number(),
  timestamp: z.number(),
  node_id: z.string(),
  host: z.string(),
  port: z.number(),
  driver: z.string(),
  event: z.string(),
})
export type NodeHistoryRecord = z.infer<typeof NodeHistoryRecordSchema>

export const PaginatedNodesSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  data: z.array(NodeHistoryRecordSchema),
})
export type PaginatedNodes = z.infer<typeof PaginatedNodesSchema>

export const EventRecordSchema = z.object({
  id: z.number(),
  timestamp: z.number(),
  topic: z.string(),
  sender: z.string(),
  payload: z.string(),
})
export type EventRecord = z.infer<typeof EventRecordSchema>

export const PaginatedEventsSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  data: z.array(EventRecordSchema),
})
export type PaginatedEvents = z.infer<typeof PaginatedEventsSchema>

export const ScheduleHistoryRecordSchema = z.object({
  id: z.number(),
  timestamp: z.number(),
  schedule_id: z.string(),
  device_id: z.string(),
  action: z.string(),
  event_type: z.string(),
  duration: z.number().nullable().optional(),
  status: z.string(),
})
export type ScheduleHistoryRecord = z.infer<typeof ScheduleHistoryRecordSchema>

export const PaginatedSchedulesHistorySchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  data: z.array(ScheduleHistoryRecordSchema),
})
export type PaginatedSchedulesHistory = z.infer<typeof PaginatedSchedulesHistorySchema>

/* Active Schedule Schemas */

export const ScheduleStateSchema = z.object({
  id: z.string(),
  enabled: z.boolean(),
  device: z.string(),
  command: z.string(),
  args: z.record(z.string(), z.unknown()).optional(),
  stop_command: z.string().nullable().optional(),
  stop_args: z.record(z.string(), z.unknown()).optional(),
  duration_seconds: z.number().optional().default(0),
  is_duration_active: z.boolean().optional().default(false),
  run_on_start: z.boolean().optional().default(false),
  time: z.string().nullable().optional(),
  interval: z.number().nullable().optional(),
  cron: z.string().nullable().optional(),
  days: z.array(z.string()).nullable().optional(),
  last_run_timestamp: z.number().nullable().optional(),
})
export type ScheduleState = z.infer<typeof ScheduleStateSchema>

export const TriggerResponseSchema = z.object({
  success: z.boolean(),
  schedule_id: z.string(),
  message: z.string(),
})
export type TriggerResponse = z.infer<typeof TriggerResponseSchema>

/* Sensor Rules Schemas */

export const RuleConditionSchema = z.object({
  device: z.string(),
  property: z.string().optional().default('value'),
  operator: z.string(),
  value: z.unknown(),
})
export type RuleCondition = z.infer<typeof RuleConditionSchema>

export const RuleActionSchema = z.object({
  device: z.string(),
  command: z.string(),
  args: z.record(z.string(), z.unknown()).optional(),
})
export type RuleAction = z.infer<typeof RuleActionSchema>

export const RuleStateSchema = z.object({
  id: z.string(),
  enabled: z.boolean(),
  condition: RuleConditionSchema,
  actions: z.array(RuleActionSchema),
  retrigger: z.boolean().optional().default(false),
  is_triggered: z.boolean().optional().default(false),
  last_sensor_value: z.unknown().optional().nullable(),
})
export type RuleState = z.infer<typeof RuleStateSchema>
