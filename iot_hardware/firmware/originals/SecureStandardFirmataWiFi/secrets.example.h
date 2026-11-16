/*==============================================================================
 * SECURE FIRMATA WIFI SECRETS TEMPLATE
 *
 * Copy this file to 'secrets.h' and fill in your WiFi credentials and 
 * node unique authentication key before compiling.
 *============================================================================*/

#ifndef SECRETS_H
#define SECRETS_H

// WiFi Network Credentials
#define SECRET_WIFI_SSID "your_network_name"
#define SECRET_WIFI_PASS "your_wpa_passphrase"

// Node Unique Authentication Key
// This key must match the 'auth_key' defined for this node in system.yaml
#define SECRET_NODE_AUTH_KEY "change_me_to_a_secure_unique_node_key_12345"

// Network Hostname reported to WiFi Router / DHCP
#define SECRET_NODE_HOSTNAME "terranode-soil-01"

// Optional Hardware TLS/SSL Socket Encryption (0 = Disabled / Pure TCP + Sysex Auth, 1 = BearSSL TLS)
// Keep as 0 for NodeMCU ESP8266 to save 30KB RAM and prevent watchdog timeouts
#define USE_TLS_SECURITY 0

#endif // SECRETS_H
