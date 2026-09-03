export enum ControlModeEnum {
  AUTO = 'AUTO',
  MANUAL_ON = 'MANUAL_ON',
  MANUAL_OFF = 'MANUAL_OFF',
  MANUAL_VALUE = 'MANUAL_VALUE',
}

export enum NodeStatusEnum {
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
}

export enum DeviceStatusEnum {
  OK = 'OK',
  ERROR = 'ERROR',
  DISCONNECTED = 'DISCONNECTED',
}

export enum DeviceTypeEnum {
  RELAY = 'relay',
  SERVO = 'servo',
  SOIL_MOISTURE = 'soil_moisture',
  BMP180 = 'bmp180',
  LDR = 'ldr',
}

export enum RawCommandTypeEnum {
  DIGITAL_WRITE = 'digital_write',
  ANALOG_WRITE = 'analog_write',
}

export const DRIVER_DISPLAY_NAMES: Record<string, string> = {
  standard_firmata: 'StandardFirmata',
  standard_firmata_wifi: 'StandardFirmataWiFi',
  mock: 'Mock NodeMCU Simulation',
}

export function formatDriverName(driver: string): string {
  if (!driver) return 'StandardFirmataWiFi'
  const key = driver.toLowerCase().trim()
  return DRIVER_DISPLAY_NAMES[key] || driver.toUpperCase()
}

export function formatControlModeLabel(mode: string): string {
  if (!mode) return 'AUTO'
  return mode.replaceAll('_', ' ')
}
