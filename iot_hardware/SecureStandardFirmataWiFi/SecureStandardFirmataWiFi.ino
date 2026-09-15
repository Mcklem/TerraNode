/*
  SecureStandardFirmataWiFi.ino
  Extension of StandardFirmataWiFi with Mandatory Node Unique Key Authentication
  and Fail-Safe Watchdog protection.

  Copyright (C) TerraNode IoT Architecture.
*/

#include <Servo.h>
#include <Wire.h>
#include <Firmata.h>

#include "utility/firmataDebug.h"
#include "wifiConfig.h"

#define I2C_WRITE                   B00000000
#define I2C_READ                    B00001000
#define I2C_READ_CONTINUOUSLY       B00010000
#define I2C_STOP_READING            B00011000
#define I2C_READ_WRITE_MODE_MASK    B00011000
#define I2C_10BIT_ADDRESS_MODE_MASK B00100000
#define I2C_END_TX_MASK             B01000000
#define I2C_STOP_TX                 1
#define I2C_RESTART_TX              0
#define I2C_MAX_QUERIES             8
#define I2C_REGISTER_NOT_SPECIFIED  -1

#define MINIMUM_SAMPLING_INTERVAL   1
#define MAX_CONN_ATTEMPTS           20

// Custom Security Sysex Command Definitions
#define SYSEX_AUTH_REQUEST          0x7E
#define SYSEX_AUTH_RESPONSE         0x7F

#define WATCHDOG_TIMEOUT_MS         5000

/*==============================================================================
 * GLOBAL VARIABLES
 *============================================================================*/

bool isNodeAuthenticated = false;
unsigned long lastTrafficMillis = 0;

int connectionAttempts = 0;
bool streamConnected = false;

int analogInputsToReport = 0;
byte reportPINs[TOTAL_PORTS];
byte previousPINs[TOTAL_PORTS];
byte portConfigInputs[TOTAL_PORTS];

unsigned long currentMillis;
unsigned long previousMillis;
unsigned int samplingInterval = 19;

struct i2c_device_info {
  byte addr;
  int reg;
  byte bytes;
  byte stopTX;
};

i2c_device_info query[I2C_MAX_QUERIES];
byte i2cRxData[64];
boolean isI2CEnabled = false;
signed char queryIndex = -1;
unsigned int i2cReadDelayTime = 0;

Servo servos[MAX_SERVOS];
byte servoPinMap[TOTAL_PINS];
byte detachedServos[MAX_SERVOS];
byte detachedServoCount = 0;
byte servoCount = 0;

boolean isResetting = false;

void setPinModeCallback(byte, int);
void reportAnalogCallback(byte analogPin, int value);
void sysexCallback(byte, byte, byte*);

/* utility functions */
void wireWrite(byte data) {
  Wire.write((byte)data);
}

byte wireRead(void) {
  return Wire.read();
}

void attachServo(byte pin, int minPulse, int maxPulse) {
  if (!isNodeAuthenticated) return;
  if (servoCount < MAX_SERVOS) {
    if (detachedServoCount > 0) {
      servoPinMap[pin] = detachedServos[detachedServoCount - 1];
      detachedServoCount--;
    } else {
      servoPinMap[pin] = servoCount;
      servoCount++;
    }
    if (minPulse > 0 && maxPulse > 0) {
      servos[servoPinMap[pin]].attach(PIN_TO_DIGITAL(pin), minPulse, maxPulse);
    } else {
      servos[servoPinMap[pin]].attach(PIN_TO_DIGITAL(pin));
    }
  } else {
    Firmata.sendString("Max servos attached");
  }
}

void detachServo(byte pin) {
  servos[servoPinMap[pin]].detach();
  if (servoPinMap[pin] == servoCount && servoCount > 0) {
    servoCount--;
  } else if (servoCount > 0) {
    detachedServoCount++;
    detachedServos[detachedServoCount - 1] = servoPinMap[pin];
  }
  servoPinMap[pin] = 255;
}

void enableI2CPins() {
  if (!isNodeAuthenticated) return;
  for (byte i = 0; i < TOTAL_PINS; i++) {
    if (IS_PIN_I2C(i)) {
      setPinModeCallback(i, PIN_MODE_I2C);
    }
  }
  isI2CEnabled = true;
  Wire.begin();
}

void disableI2CPins() {
  isI2CEnabled = false;
  queryIndex = -1;
}

void readAndReportData(byte address, int theRegister, byte numBytes, byte stopTX) {
  if (!isNodeAuthenticated) return;
  if (theRegister != I2C_REGISTER_NOT_SPECIFIED) {
    Wire.beginTransmission(address);
    wireWrite((byte)theRegister);
    Wire.endTransmission(stopTX);
    if (i2cReadDelayTime > 0) delayMicroseconds(i2cReadDelayTime);
  } else {
    theRegister = 0;
  }

  Wire.requestFrom(address, numBytes);
  if (numBytes < Wire.available()) {
    Firmata.sendString("I2C: Too many bytes received");
  } else if (numBytes > Wire.available()) {
    Firmata.sendString("I2C: Too few bytes received");
    numBytes = Wire.available();
  }

  i2cRxData[0] = address;
  i2cRxData[1] = theRegister;
  for (int i = 0; i < numBytes && Wire.available(); i++) {
    i2cRxData[2 + i] = wireRead();
  }
  Firmata.sendSysex(SYSEX_I2C_REPLY, numBytes + 2, i2cRxData);
}

void outputPort(byte portNumber, byte portValue, byte forceSend) {
  portValue = portValue & portConfigInputs[portNumber];
  if (forceSend || previousPINs[portNumber] != portValue) {
    Firmata.sendDigitalPort(portNumber, portValue);
    previousPINs[portNumber] = portValue;
  }
}

void checkDigitalInputs(void) {
  if (!isNodeAuthenticated) return;
  if (TOTAL_PORTS > 0 && reportPINs[0]) outputPort(0, readPort(0, portConfigInputs[0]), false);
  if (TOTAL_PORTS > 1 && reportPINs[1]) outputPort(1, readPort(1, portConfigInputs[1]), false);
  if (TOTAL_PORTS > 2 && reportPINs[2]) outputPort(2, readPort(2, portConfigInputs[2]), false);
  if (TOTAL_PORTS > 3 && reportPINs[3]) outputPort(3, readPort(3, portConfigInputs[3]), false);
}

void setPinModeCallback(byte pin, int mode) {
  if (Firmata.getPinMode(pin) == PIN_MODE_IGNORE) return;
  if (!isNodeAuthenticated && mode != OUTPUT && mode != PIN_MODE_ANALOG) return;

  if (Firmata.getPinMode(pin) == PIN_MODE_I2C && isI2CEnabled && mode != PIN_MODE_I2C) {
    disableI2CPins();
  }
  if (IS_PIN_DIGITAL(pin) && mode != PIN_MODE_SERVO) {
    if (servoPinMap[pin] < MAX_SERVOS && servos[servoPinMap[pin]].attached()) {
      detachServo(pin);
    }
  }
  if (IS_PIN_ANALOG(pin)) {
    reportAnalogCallback(PIN_TO_ANALOG(pin), mode == PIN_MODE_ANALOG ? 1 : 0);
  }
  if (IS_PIN_DIGITAL(pin)) {
    if (mode == INPUT || mode == PIN_MODE_PULLUP) {
      portConfigInputs[pin / 8] |= (1 << (pin & 7));
    } else {
      portConfigInputs[pin / 8] &= ~(1 << (pin & 7));
    }
  }
  Firmata.setPinState(pin, 0);
  switch (mode) {
    case PIN_MODE_ANALOG:
      if (IS_PIN_ANALOG(pin)) {
        if (IS_PIN_DIGITAL(pin)) pinMode(PIN_TO_DIGITAL(pin), INPUT);
        Firmata.setPinMode(pin, PIN_MODE_ANALOG);
      }
      break;
    case INPUT:
      if (IS_PIN_DIGITAL(pin)) {
        pinMode(PIN_TO_DIGITAL(pin), INPUT);
        Firmata.setPinMode(pin, INPUT);
      }
      break;
    case PIN_MODE_PULLUP:
      if (IS_PIN_DIGITAL(pin)) {
        pinMode(PIN_TO_DIGITAL(pin), INPUT_PULLUP);
        Firmata.setPinMode(pin, PIN_MODE_PULLUP);
        Firmata.setPinState(pin, 1);
      }
      break;
    case OUTPUT:
      if (IS_PIN_DIGITAL(pin)) {
        pinMode(PIN_TO_DIGITAL(pin), OUTPUT);
        digitalWrite(PIN_TO_DIGITAL(pin), LOW);
        Firmata.setPinMode(pin, OUTPUT);
      }
      break;
    case PIN_MODE_PWM:
      if (IS_PIN_PWM(pin)) {
        pinMode(PIN_TO_PWM(pin), OUTPUT);
        analogWrite(PIN_TO_PWM(pin), 0);
        Firmata.setPinMode(pin, PIN_MODE_PWM);
      }
      break;
    case PIN_MODE_SERVO:
      if (IS_PIN_DIGITAL(pin)) {
        Firmata.setPinMode(pin, PIN_MODE_SERVO);
        if (servoPinMap[pin] == 255 || !servos[servoPinMap[pin]].attached()) {
          attachServo(pin, -1, -1);
        }
      }
      break;
    case PIN_MODE_I2C:
      if (IS_PIN_I2C(pin)) Firmata.setPinMode(pin, PIN_MODE_I2C);
      break;
  }
}

void setPinValueCallback(byte pin, int value) {
  if (!isNodeAuthenticated) return;
  if (pin < TOTAL_PINS && IS_PIN_DIGITAL(pin)) {
    if (Firmata.getPinMode(pin) == OUTPUT) {
      Firmata.setPinState(pin, value);
      digitalWrite(PIN_TO_DIGITAL(pin), value);
    }
  }
}

void analogWriteCallback(byte pin, int value) {
  if (!isNodeAuthenticated) return;
  if (pin < TOTAL_PINS) {
    switch (Firmata.getPinMode(pin)) {
      case PIN_MODE_SERVO:
        if (IS_PIN_DIGITAL(pin)) servos[servoPinMap[pin]].write(value);
        Firmata.setPinState(pin, value);
        break;
      case PIN_MODE_PWM:
        if (IS_PIN_PWM(pin)) analogWrite(PIN_TO_PWM(pin), value);
        Firmata.setPinState(pin, value);
        break;
    }
  }
}

void digitalWriteCallback(byte port, int value) {
  if (!isNodeAuthenticated) return;
  byte pin, lastPin, pinValue, mask = 1, pinWriteMask = 0;
  if (port < TOTAL_PORTS) {
    lastPin = port * 8 + 8;
    if (lastPin > TOTAL_PINS) lastPin = TOTAL_PINS;
    for (pin = port * 8; pin < lastPin; pin++) {
      if (IS_PIN_DIGITAL(pin)) {
        if (Firmata.getPinMode(pin) == OUTPUT || Firmata.getPinMode(pin) == INPUT) {
          pinValue = ((byte)value & mask) ? 1 : 0;
          if (Firmata.getPinMode(pin) == OUTPUT) pinWriteMask |= mask;
          Firmata.setPinState(pin, pinValue);
        }
      }
      mask = mask << 1;
    }
    writePort(port, (byte)value, pinWriteMask);
  }
}

void reportAnalogCallback(byte analogPin, int value) {
  if (!isNodeAuthenticated) return;
  if (analogPin < TOTAL_ANALOG_PINS) {
    if (value == 0) {
      analogInputsToReport = analogInputsToReport & ~(1 << analogPin);
    } else {
      analogInputsToReport = analogInputsToReport | (1 << analogPin);
      if (!isResetting) Firmata.sendAnalog(analogPin, analogRead(analogPin));
    }
  }
}

void reportDigitalCallback(byte port, int value) {
  if (!isNodeAuthenticated) return;
  if (port < TOTAL_PORTS) {
    reportPINs[port] = (byte)value;
    if (value) outputPort(port, readPort(port, portConfigInputs[port]), true);
  }
}

void sysexCallback(byte command, byte argc, byte *argv) {
  if (command == SYSEX_AUTH_REQUEST) {
    // Reconstruct key string from Firmata 7-bit encoded bytes
    char keyBuffer[64];
    byte keyLen = 0;
    for (byte i = 0; i + 1 < argc && keyLen < 63; i += 2) {
      byte charByte = argv[i] | (argv[i + 1] << 7);
      keyBuffer[keyLen++] = (char)charByte;
    }
    keyBuffer[keyLen] = '\0';

    byte authStatus = 0;
    if (strcmp(keyBuffer, node_auth_key) == 0) {
      isNodeAuthenticated = true;
      lastTrafficMillis = millis();
      authStatus = 1;
    } else {
      isNodeAuthenticated = false;
      authStatus = 0;
    }

    byte reply[1] = { authStatus };
    Firmata.sendSysex(SYSEX_AUTH_RESPONSE, 1, reply);
    return;
  }

  // System discovery queries (read-only capability & pin structure queries)
  switch (command) {
    case CAPABILITY_QUERY:
      Firmata.write(START_SYSEX);
      Firmata.write(CAPABILITY_RESPONSE);
      for (byte pin = 0; pin < TOTAL_PINS; pin++) {
        if (IS_PIN_DIGITAL(pin)) {
          Firmata.write((byte)INPUT);
          Firmata.write(1);
          Firmata.write((byte)PIN_MODE_PULLUP);
          Firmata.write(1);
          Firmata.write((byte)OUTPUT);
          Firmata.write(1);
        }
        if (IS_PIN_ANALOG(pin)) {
          Firmata.write(PIN_MODE_ANALOG);
          Firmata.write(10);
        }
        if (IS_PIN_PWM(pin)) {
          Firmata.write(PIN_MODE_PWM);
          Firmata.write(DEFAULT_PWM_RESOLUTION);
        }
        if (IS_PIN_DIGITAL(pin)) {
          Firmata.write(PIN_MODE_SERVO);
          Firmata.write(14);
        }
        if (IS_PIN_I2C(pin)) {
          Firmata.write(PIN_MODE_I2C);
          Firmata.write(1);
        }
        Firmata.write(127);
      }
      Firmata.write(END_SYSEX);
      stream.flush();
      return;
    case PIN_STATE_QUERY:
      if (argc > 0) {
        byte pin = argv[0];
        Firmata.write(START_SYSEX);
        Firmata.write(PIN_STATE_RESPONSE);
        Firmata.write(pin);
        if (pin < TOTAL_PINS) {
          Firmata.write(Firmata.getPinMode(pin));
          Firmata.write((byte)Firmata.getPinState(pin) & 0x7F);
          if (Firmata.getPinState(pin) & 0xFF80) Firmata.write((byte)(Firmata.getPinState(pin) >> 7) & 0x7F);
          if (Firmata.getPinState(pin) & 0xC000) Firmata.write((byte)(Firmata.getPinState(pin) >> 14) & 0x7F);
        }
        Firmata.write(END_SYSEX);
        stream.flush();
      }
      return;
    case ANALOG_MAPPING_QUERY:
      Firmata.write(START_SYSEX);
      Firmata.write(ANALOG_MAPPING_RESPONSE);
      for (byte pin = 0; pin < TOTAL_PINS; pin++) {
        Firmata.write(IS_PIN_ANALOG(pin) ? PIN_TO_ANALOG(pin) : 127);
      }
      Firmata.write(END_SYSEX);
      stream.flush();
      return;
    case SAMPLING_INTERVAL:
      if (argc > 1) {
        samplingInterval = argv[0] + (argv[1] << 7);
        if (samplingInterval < MINIMUM_SAMPLING_INTERVAL) {
          samplingInterval = MINIMUM_SAMPLING_INTERVAL;
        }
      }
      return;
  }

  // ALL HARDWARE MUTATION COMMANDS (I2C, SERVO, PIN WRITES) ARE STRICTLY BLOCKED UNTIL AUTHENTICATED:
  if (!isNodeAuthenticated) return;

  byte slaveAddress, data, stopTX;
  int slaveRegister;
  unsigned int delayTime;

  switch (command) {
    case I2C_REQUEST:
      slaveAddress = argv[0];
      if (argc == 6) {
        slaveRegister = argv[2] + (argv[3] << 7);
        data = argv[4] + (argv[5] << 7);
      } else {
        slaveRegister = I2C_REGISTER_NOT_SPECIFIED;
        data = argv[2] + (argv[3] << 7);
      }
      readAndReportData(slaveAddress, (int)slaveRegister, data, I2C_STOP_TX);
      break;
    case I2C_CONFIG:
      delayTime = (argv[0] + (argv[1] << 7));
      if (argc > 1 && delayTime > 0) i2cReadDelayTime = delayTime;
      if (!isI2CEnabled) enableI2CPins();
      break;
    case SERVO_CONFIG:
      if (argc > 4) {
        byte pin = argv[0];
        int minPulse = argv[1] + (argv[2] << 7);
        int maxPulse = argv[3] + (argv[4] << 7);
        if (IS_PIN_DIGITAL(pin)) {
          if (servoPinMap[pin] < MAX_SERVOS && servos[servoPinMap[pin]].attached()) detachServo(pin);
          attachServo(pin, minPulse, maxPulse);
          setPinModeCallback(pin, PIN_MODE_SERVO);
        }
      }
      break;
  }
}

void systemResetCallback() {
  isResetting = true;
  isNodeAuthenticated = false;
  if (isI2CEnabled) disableI2CPins();

  for (byte i = 0; i < TOTAL_PORTS; i++) {
    reportPINs[i] = false;
    portConfigInputs[i] = 0;
    previousPINs[i] = 0;
  }

  for (byte i = 0; i < TOTAL_PINS; i++) {
    if (IS_PIN_ANALOG(i)) {
      setPinModeCallback(i, PIN_MODE_ANALOG);
    } else if (IS_PIN_DIGITAL(i)) {
      setPinModeCallback(i, OUTPUT);
    }
    servoPinMap[i] = 255;
  }
  analogInputsToReport = 0;
  detachedServoCount = 0;
  servoCount = 0;
  isResetting = false;
}

void hostConnectionCallback(byte state) {
  if (state == HOST_CONNECTION_DISCONNECTED) {
    isNodeAuthenticated = false;
    systemResetCallback();
  }
}

void ignorePins() {
#ifdef IS_IGNORE_PIN
  for (byte i = 0; i < TOTAL_PINS; i++) {
    if (IS_IGNORE_PIN(i)) Firmata.setPinMode(i, PIN_MODE_IGNORE);
  }
#endif
}

void initTransport() {
  stream.attach(hostConnectionCallback);
#if defined(ESP8266)
  WiFi.hostname(node_hostname);
#elif defined(ESP32)
  WiFi.setHostname(node_hostname);
#endif
  stream.begin(ssid, wpa_passphrase);
  while (WiFi.status() != WL_CONNECTED && ++connectionAttempts <= MAX_CONN_ATTEMPTS) {
    delay(500);
  }
}

void initFirmata() {
  Firmata.setFirmwareVersion(2, 5);
  Firmata.attach(ANALOG_MESSAGE, analogWriteCallback);
  Firmata.attach(DIGITAL_MESSAGE, digitalWriteCallback);
  Firmata.attach(REPORT_ANALOG, reportAnalogCallback);
  Firmata.attach(REPORT_DIGITAL, reportDigitalCallback);
  Firmata.attach(SET_PIN_MODE, setPinModeCallback);
  Firmata.attach(SET_DIGITAL_PIN_VALUE, setPinValueCallback);
  Firmata.attach(START_SYSEX, sysexCallback);
  Firmata.attach(SYSTEM_RESET, systemResetCallback);

  ignorePins();
  Firmata.begin(stream);
  systemResetCallback();
}

void setup() {
  DEBUG_BEGIN(9600);
  initTransport();
  initFirmata();
  lastTrafficMillis = millis();
}

void loop() {
  byte pin, analogPin;
  checkDigitalInputs();

  bool hadTraffic = false;
  while (Firmata.available()) {
    hadTraffic = true;
    Firmata.processInput();
  }

  if (hadTraffic) {
    lastTrafficMillis = millis();
  }

  // Fail-Safe Watchdog: If authenticated but no traffic received for WATCHDOG_TIMEOUT_MS, revoke auth & safe reset
  if (isNodeAuthenticated && (millis() - lastTrafficMillis > WATCHDOG_TIMEOUT_MS)) {
    isNodeAuthenticated = false;
    systemResetCallback();
  }

  currentMillis = millis();
  if (isNodeAuthenticated && (currentMillis - previousMillis > samplingInterval)) {
    previousMillis += samplingInterval;
    for (pin = 0; pin < TOTAL_PINS; pin++) {
      if (IS_PIN_ANALOG(pin) && Firmata.getPinMode(pin) == PIN_MODE_ANALOG) {
        analogPin = PIN_TO_ANALOG(pin);
        if (analogInputsToReport & (1 << analogPin)) {
          Firmata.sendAnalog(analogPin, analogRead(analogPin));
        }
      }
    }
    if (queryIndex > -1) {
      for (byte i = 0; i < queryIndex + 1; i++) {
        readAndReportData(query[i].addr, query[i].reg, query[i].bytes, query[i].stopTX);
      }
    }
  }

  stream.maintain();
}
