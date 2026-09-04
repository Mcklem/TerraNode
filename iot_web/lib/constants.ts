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
  INITIALIZING = 'INITIALIZING',
  OK = 'OK',
  WARNING = 'WARNING',
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

export enum NodeDriverEnum {
  STANDARD_FIRMATA_WIFI = 'standard_firmata_wifi',
  SECURE_STANDARD_FIRMATA_WIFI = 'secure_standard_firmata_wifi',
  STANDARD_FIRMATA = 'standard_firmata',
  SECURE_FIRMATA = 'secure_firmata',
  FIRMATA = 'firmata',
  MOCK = 'mock',
}

export const DRIVER_DISPLAY_NAMES: Record<string, string> = {
  [NodeDriverEnum.STANDARD_FIRMATA_WIFI]: 'StandardFirmataWiFi',
  [NodeDriverEnum.SECURE_STANDARD_FIRMATA_WIFI]: 'SecureStandardFirmataWiFi',
  [NodeDriverEnum.STANDARD_FIRMATA]: 'StandardFirmata',
  [NodeDriverEnum.SECURE_FIRMATA]: 'SecureFirmata',
  [NodeDriverEnum.FIRMATA]: 'StandardFirmataWiFi',
  [NodeDriverEnum.MOCK]: 'Mock NodeMCU',
}

export function formatDriverName(driver: string): string {
  if (!driver) return 'StandardFirmataWiFi'
  const key = driver.toLowerCase().trim()
  return DRIVER_DISPLAY_NAMES[key] || driver
}

export function formatControlModeLabel(mode: string): string {
  if (!mode) return 'AUTO'
  return mode.replaceAll('_', ' ')
}
