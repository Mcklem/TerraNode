import { apiFetch } from './terranode-api'

export interface ValidationIssue {
  field: string
  message: string
  level: 'error' | 'warning' | 'info'
  line?: number
}

export interface ValidationResult {
  valid: boolean
  errors: ValidationIssue[]
  warnings: ValidationIssue[]
  infos: ValidationIssue[]
}

export interface EnvChange {
  variable: string
  path: string
  masked_value: string
  action: 'created' | 'updated'
}

export interface DiffResult {
  unified_diff: string
  has_changes: boolean
  added_keys: string[]
  removed_keys: string[]
  modified_keys: string[]
  env_changes?: EnvChange[]
  proposed_yaml?: string
}

export interface BackupMetadata {
  id: string
  filename: string
  timestamp: string
  created_at: number
  author: string
  description: string
  checksum: string
  size_bytes: number
  diff_summary?: {
    added?: string[]
    removed?: string[]
    modified?: string[]
  }
}

export interface ConfigStatus {
  active_config_path: string
  saved_checksum: string
  runtime_checksum: string | null
  is_synchronized: boolean
  last_saved_at: string | null
  last_applied_at: string | null
  counts: {
    nodes: number
    devices: number
    rules: number
    schedules: number
  }
  validation: ValidationResult
}

export interface NodeConfig {
  driver: string
  host?: string
  port?: number
  auth_key?: string
  use_tls?: boolean
  enabled?: boolean
  arduino_wait?: number
  max_retries?: number
  timeout?: number
  [key: string]: any
}

export interface DeviceConfig {
  type: string
  node: string
  pin?: string
  bus?: string
  address?: string | number
  oss?: number
  poll_interval?: number
  active_low?: boolean
  min_angle?: number
  max_angle?: number
  min_pulse?: number
  max_pulse?: number
  calibration?: {
    dry?: number
    wet?: number
    dark?: number
    light?: number
    [key: string]: any
  }
  unit?: string
  [key: string]: any
}

export interface RuleAction {
  device?: string
  command?: string
  args?: Record<string, any>
  type?: 'actuator' | 'notification'
  channel?: 'email' | 'telegram' | 'webhook' | 'all'
  webhook_id?: string
  title?: string
  message?: string
}

export interface RuleConfig {
  enabled?: boolean
  retrigger?: boolean
  cooldown?: number
  recovery_message?: string
  condition: {
    device: string
    property?: string
    operator: string
    value: any
  }
  actions: RuleAction[]
}

export interface ScheduleConfig {
  enabled?: boolean
  device: string
  command: string
  args?: Record<string, any>
  stop_command?: string
  stop_args?: Record<string, any>
  duration?: number
  interval?: number
  run_on_start?: boolean
  time?: string
  days?: string[]
  cron?: string
}

export interface EmailNotificationConfig {
  enabled: boolean
  smtp_host: string
  smtp_port: number
  use_tls: boolean
  username: string
  password?: string
  from_address: string
  to_addresses: string[]
}

export interface TelegramNotificationConfig {
  enabled: boolean
  bot_token?: string
  chat_id: string
}

export interface WebhookConfig {
  name?: string
  enabled: boolean
  url: string
  method: 'GET' | 'POST' | 'PUT'
  headers?: Record<string, string>
  payload_template?: string
}

export interface NotificationsConfig {
  email?: EmailNotificationConfig
  telegram?: TelegramNotificationConfig
  webhooks?: Record<string, WebhookConfig>
}

export interface NotificationStatus {
  email: {
    enabled: boolean
    configured: boolean
    smtp_host: string
    to_addresses_count: number
  }
  telegram: {
    enabled: boolean
    configured: boolean
    chat_id: string
  }
  webhooks: {
    total: number
    enabled_count: number
    items: Array<{
      id: string
      name: string
      url: string
      method: string
      enabled: boolean
    }>
  }
}

export interface NotificationTestResult {
  success: boolean
  channel: string
  target?: string
  message?: string
  error?: string
}

export interface NormalizedConfig {
  system?: {
    name?: string
    version?: string
    database?: string
    log_readings?: boolean
    log_rule_evaluations?: boolean
    [key: string]: any
  }
  nodes: Record<string, NodeConfig>
  devices: Record<string, DeviceConfig>
  rules: Record<string, RuleConfig>
  schedules: Record<string, ScheduleConfig>
  notifications?: NotificationsConfig
  [key: string]: any
}

export interface ConfigResponse {
  raw_yaml: string
  config: NormalizedConfig
  status: ConfigStatus
}

export interface SaveConfigResponse {
  success: boolean
  checksum: string
  backup_id: string
  diff: DiffResult
  env_changes?: EnvChange[]
  message: string
}

export interface ApplyConfigResponse {
  success: boolean
  reloaded_at: string
  runtime_checksum: string
  message: string
  report: Record<string, any>
}

export interface SchemaMetadata {
  supported_drivers: string[]
  supported_device_types: string[]
  device_specs: Record<
    string,
    {
      type: string
      category: 'sensor' | 'actuator'
      commands: string[]
      properties: string[]
      bus: 'pin' | 'i2c'
      default_pin?: string
    }
  >
  available_pins: string[]
  comparison_operators: string[]
}

/* ==============================================================================
 * API METHODS
 * ============================================================================== */

export const fetchConfig = (masked = true, signal?: AbortSignal): Promise<ConfigResponse> =>
  apiFetch<ConfigResponse>(`/config?masked=${masked}`, undefined, { signal })

export const validateConfig = (payload: { raw_yaml?: string; config?: any }): Promise<ValidationResult> =>
  apiFetch<ValidationResult>('/config/validate', undefined, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const fetchConfigDiff = (
  payload: string | { proposed_yaml?: string; visual_model?: any }
): Promise<DiffResult> => {
  const body = typeof payload === 'string' ? { proposed_yaml: payload } : payload
  return apiFetch<DiffResult>('/config/diff', undefined, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export const convertYamlToModel = (raw_yaml: string): Promise<{ config: NormalizedConfig }> =>
  apiFetch<{ config: NormalizedConfig }>('/config/yaml-to-model', undefined, {
    method: 'POST',
    body: JSON.stringify({ raw_yaml }),
  })

export const saveRawYamlConfig = (payload: {
  raw_yaml: string
  base_checksum?: string
  author?: string
  description?: string
}): Promise<SaveConfigResponse> =>
  apiFetch<SaveConfigResponse>('/config/save', undefined, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const saveVisualConfig = (payload: {
  visual_model: NormalizedConfig
  base_checksum?: string
  author?: string
  description?: string
}): Promise<SaveConfigResponse> =>
  apiFetch<SaveConfigResponse>('/config/save', undefined, {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const applyConfig = (payload?: { force?: boolean }): Promise<ApplyConfigResponse> =>
  apiFetch<ApplyConfigResponse>('/config/apply', undefined, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })

export const fetchConfigBackups = (signal?: AbortSignal): Promise<BackupMetadata[]> =>
  apiFetch<BackupMetadata[]>('/config/backups', undefined, { signal })

export const fetchBackupDetail = (
  backupId: string,
  signal?: AbortSignal
): Promise<{ metadata: BackupMetadata; raw_yaml: string }> =>
  apiFetch<{ metadata: BackupMetadata; raw_yaml: string }>(
    `/config/backups/${encodeURIComponent(backupId)}`,
    undefined,
    { signal }
  )

export const restoreConfigBackup = (
  backupId: string,
  author = 'operator'
): Promise<{ success: boolean; checksum: string; pre_restore_backup_id: string; message: string }> =>
  apiFetch(`/config/backups/${encodeURIComponent(backupId)}/restore`, undefined, {
    method: 'POST',
    body: JSON.stringify({ author }),
  })

export const deleteConfigBackup = (backupId: string): Promise<{ success: boolean; message: string }> =>
  apiFetch(`/config/backups/${encodeURIComponent(backupId)}`, undefined, {
    method: 'DELETE',
  })

export const fetchConfigSchema = (signal?: AbortSignal): Promise<SchemaMetadata> =>
  apiFetch<SchemaMetadata>('/config/schema', undefined, { signal })

export const fetchNotificationStatus = (signal?: AbortSignal): Promise<NotificationStatus> =>
  apiFetch<NotificationStatus>('/notifications/status', undefined, { signal })

export const testNotificationChannel = (payload: {
  channel: 'email' | 'telegram' | 'webhook'
  webhook_id?: string
  config_override?: any
  message?: string
}): Promise<NotificationTestResult> =>
  apiFetch<NotificationTestResult>('/notifications/test', undefined, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
