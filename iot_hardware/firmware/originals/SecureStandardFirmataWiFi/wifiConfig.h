/*==============================================================================
 * SECURE WIFI CONFIGURATION
 *
 * Configured for SecureStandardFirmataWiFi with optional TLS encryption 
 * and Mandatory Node Key Authentication.
 *============================================================================*/

#ifndef WIFI_CONFIG_H
#define WIFI_CONFIG_H

#if __has_include("secrets.h")
  #include "secrets.h"
#endif

// Default WiFi Credentials fallback if secrets.h is not used
#ifndef SECRET_WIFI_SSID
  #define SECRET_WIFI_SSID "your_network_name"
#endif

#ifndef SECRET_WIFI_PASS
  #define SECRET_WIFI_PASS "your_wpa_passphrase"
#endif

#ifndef SECRET_NODE_AUTH_KEY
  #define SECRET_NODE_AUTH_KEY "default_secure_terranode_key_3030"
#endif

#ifndef SECRET_NODE_HOSTNAME
  #define SECRET_NODE_HOSTNAME "terranode-node"
#endif

#ifndef USE_TLS_SECURITY
  #define USE_TLS_SECURITY 0
#endif

#if USE_TLS_SECURITY == 1
  #define IS_TLS_ENABLED 1
#else
  #define IS_TLS_ENABLED 0
#endif

// Node Unique Authentication Key & Hostname
const char node_auth_key[] = SECRET_NODE_AUTH_KEY;
const char node_hostname[] = SECRET_NODE_HOSTNAME;

// STEP 1: Hardware Selection
#if defined(ESP8266)
  #define ESP8266_WIFI
  #include <ESP8266WiFi.h>
  #include "utility/WiFiClientStream.h"
  #include "utility/WiFiServerStream.h"
  #define WIFI_LIB_INCLUDED
#elif defined(ARDUINO_SAMD_MKRWIFI1010) || defined(WIFI_NINA)
  #define WIFI_NINA
  #include <WiFiNINA.h>
  #include "utility/WiFiClientStream.h"
  #include "utility/WiFiServerStream.h"
  #define WIFI_LIB_INCLUDED
#else
  // Default to standard WiFi library
  #include <WiFi.h>
  #include "utility/WiFiClientStream.h"
  #include "utility/WiFiServerStream.h"
  #define WIFI_LIB_INCLUDED
#endif

// STEP 2: Wireless SSID & Passphrase
char ssid[] = SECRET_WIFI_SSID;
#define WIFI_WPA_SECURITY
char wpa_passphrase[] = SECRET_WIFI_PASS;

// STEP 3: Server Port
#define SERVER_PORT 3030

// STEP 4: Server Stream Instance
WiFiServerStream stream(SERVER_PORT);

// STEP 5: Pin Ignore Macros
#if defined(ESP8266_WIFI) && defined(SERIAL_DEBUG)
  #define IS_IGNORE_PIN(p)  ((p) == 1)
#endif

#endif // WIFI_CONFIG_H
