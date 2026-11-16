import { z } from 'zod'

export const ControlModeSchema = z.enum(['AUTO', 'MANUAL_ON', 'MANUAL_OFF', 'MANUAL_VALUE'])
export type Mode = z.infer<typeof ControlModeSchema>

export const NodeStatusSchema = z.enum(['CONNECTED', 'DISCONNECTED', 'RECONNECTING', 'ERROR'])
export type NodeStatus = z.infer<typeof NodeStatusSchema>

export const DeviceStatusSchema = z.enum(['INITIALIZING', 'OK', 'WARNING', 'ERROR', 'DISCONNECTED'])
export type DeviceStatus = z.infer<typeof DeviceStatusSchema>

export const NodeInfoSchema = z.object({
  id: z.string(),
  connected: z.boolean(),
  driver: z.string(),
  host: z.string(),
  port: z.number(),
  enabled: z.boolean(),
  status: NodeStatusSchema,
  last_error: z.string().nullable().optional(),
}).passthrough()
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

export const DeviceCategorySchema = z.enum(['sensor', 'actuator'])
export type DeviceCategory = z.infer<typeof DeviceCategorySchema>

export const DeviceSchema = z.object({
  id: z.string(),
  type: z.string(),
  category: z.enum(['sensor', 'actuator']).optional().default('sensor'),
  node_id: z.string(),
  status: DeviceStatusSchema,
  control_mode: ControlModeSchema,
  override_active: z.boolean(),
  current_state: DeviceStateSchema,
}).passthrough()
export type Device = z.infer<typeof DeviceSchema>

export function isSensor(device: Device): boolean {
  return device.category === 'sensor'
}

export function isActuator(device: Device): boolean {
  return device.category === 'actuator'
}

export const HealthSchema = z.object({
  status: z.string().optional().default('OK'),
  total_nodes: z.number().optional().default(0),
  connected_nodes: z.number().optional().default(0),
  total_devices: z.number().optional().default(0),
  message: z.string().nullable().optional(),
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
  device: z.string().optional().nullable(),
  command: z.string().optional().nullable(),
  args: z.record(z.string(), z.unknown()).optional().nullable(),
  stop_command: z.string().nullable().optional(),
  stop_args: z.record(z.string(), z.unknown()).optional().nullable(),
  duration_seconds: z.number().optional().default(0),
  is_duration_active: z.boolean().optional().default(false),
  run_on_start: z.boolean().optional().default(false),
  time: z.string().nullable().optional(),
  interval: z.number().nullable().optional(),
  cron: z.string().nullable().optional(),
  days: z.array(z.string()).nullable().optional(),
  last_run_timestamp: z.number().nullable().optional(),
}).passthrough()
export type ScheduleState = z.infer<typeof ScheduleStateSchema>

export const TriggerResponseSchema = z.object({
  success: z.boolean(),
  schedule_id: z.string(),
  message: z.string(),
}).passthrough()
export type TriggerResponse = z.infer<typeof TriggerResponseSchema>

/* Sensor Rules Schemas */

export const RuleConditionSchema = z.object({
  device: z.string(),
  property: z.string().optional().default('value'),
  operator: z.string(),
  value: z.unknown(),
}).passthrough()
export type RuleCondition = z.infer<typeof RuleConditionSchema>

export const RuleActionSchema = z.object({
  device: z.string().optional().nullable(),
  command: z.string().optional().nullable(),
  args: z.record(z.string(), z.unknown()).optional().nullable(),
  type: z.string().optional().nullable(),
  channel: z.string().optional().nullable(),
  webhook_id: z.string().optional().nullable(),
  title: z.string().optional().nullable(),
  message: z.string().optional().nullable(),
}).passthrough()
export type RuleAction = z.infer<typeof RuleActionSchema>

export const RuleStateSchema = z.object({
  id: z.string(),
  enabled: z.boolean(),
  condition: RuleConditionSchema,
  actions: z.array(RuleActionSchema),
  retrigger: z.boolean().optional().default(false),
  cooldown: z.number().optional().nullable(),
  recovery_message: z.string().optional().nullable(),
  is_triggered: z.boolean().optional().default(false),
  last_sensor_value: z.unknown().optional().nullable(),
}).passthrough()
export type RuleState = z.infer<typeof RuleStateSchema>

/* Firmware Studio Schemas */

export const BoardProfileSchema = z.object({
  fqbn: z.string(),
  name: z.string().optional().nullable(),
  architecture: z.string().optional().nullable(),
  flash_size: z.string().optional().nullable(),
})
export type BoardProfile = z.infer<typeof BoardProfileSchema>

export const ParameterOptionSchema = z.object({
  value: z.union([z.string(), z.number()]),
  label: z.string(),
})
export type ParameterOption = z.infer<typeof ParameterOptionSchema>

export const FirmwareParameterSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.enum([
    'string',
    'password',
    'secret',
    'ip',
    'port',
    'number',
    'boolean',
    'select',
    'pin',
    'interval',
  ]),
  required: z.boolean().optional().default(true),
  default: z.unknown().optional().nullable(),
  sensitive: z.boolean().optional().default(false),
  description: z.string().optional().nullable(),
  min: z.number().optional().nullable(),
  max: z.number().optional().nullable(),
  step: z.number().optional().nullable(),
  min_length: z.number().optional().nullable(),
  max_length: z.number().optional().nullable(),
  options: z.array(ParameterOptionSchema).optional().nullable(),
  validation_regex: z.string().optional().nullable(),
})
export type FirmwareParameter = z.infer<typeof FirmwareParameterSchema>

export const FirmwareDependencySchema = z.object({
  name: z.string(),
  version: z.string().optional().nullable(),
})

export const FirmwareBuildOptionsSchema = z.object({
  optimize: z.boolean().optional().default(true),
  cpu_freq: z.number().optional().nullable(),
  flash_mode: z.string().optional().nullable(),
})

export const FirmwareManifestSchema = z.object({
  id: z.string(),
  name: z.string(),
  description: z.string(),
  version: z.string(),
  category: z.string().optional().default('firmata'),
  author: z.string().optional().nullable(),
  board: BoardProfileSchema,
  upload_methods: z.array(z.string()).optional().default(['web_serial', 'binary_download', 'source_download']),
  parameters: z.array(FirmwareParameterSchema).optional().default([]),
  dependencies: z.array(FirmwareDependencySchema).optional().default([]),
  build: FirmwareBuildOptionsSchema.optional().default({ optimize: true }),
  readme: z.string().optional().nullable(),
})
export type FirmwareManifest = z.infer<typeof FirmwareManifestSchema>

export const BuildRecordSchema = z.object({
  id: z.string(),
  timestamp: z.number(),
  template_id: z.string(),
  template_version: z.string(),
  target_fqbn: z.string(),
  status: z.string(),
  status_message: z.string().optional().nullable(),
  compiler_output: z.string().optional().nullable(),
  binary_filename: z.string().optional().nullable(),
  binary_size_bytes: z.number().optional().nullable(),
  checksum_sha256: z.string().optional().nullable(),
  completed_at: z.number().optional().nullable(),
  public_params: z.record(z.string(), z.unknown()).optional().nullable(),
  generated_files_count: z.number().optional(),
})
export type BuildRecord = z.infer<typeof BuildRecordSchema>

export const PaginatedFirmwareHistorySchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  builds: z.array(BuildRecordSchema),
})
export type PaginatedFirmwareHistory = z.infer<typeof PaginatedFirmwareHistorySchema>

