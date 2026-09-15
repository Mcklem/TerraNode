import asyncio
import ssl
import time
from typing import Optional
from pymata4 import pymata4

from utils.logging import get_logger
from .firmata_node import FirmataNode

SYSEX_AUTH_REQUEST = 0x7E
SYSEX_AUTH_RESPONSE = 0x7F


class SecureFirmataNode(FirmataNode):
    """Secure Pymata4 / SecureStandardFirmataWiFi node implementation.

    Enforces TLS socket connection option, Node Unique Key Sysex Authentication, 
    and Active Heartbeat keepalive.
    """

    def __init__(
        self,
        node_id: str,
        driver: str,
        host: str,
        port: int = 3030,
        enabled: bool = True,
        auth_key: Optional[str] = None,
        use_tls: bool = False,
        **kwargs,
    ):
        super().__init__(node_id, driver, host, port, enabled, **kwargs)
        self.auth_key = auth_key
        self.use_tls = use_tls
        self._authenticated = False
        self._logger = get_logger("SecureFirmataNode", node_id=self.id)

    async def connect(self) -> bool:
        """Establish TLS socket connection (if configured) and authenticate with node unique key."""
        connected = await super().connect()
        if not connected or not self._board:
            return False

        if not self.auth_key:
            err_msg = f"MISSING_AUTH_KEY: SecureNode '{self.id}' has no 'auth_key' configured in system.yaml."
            self._logger.warning(err_msg)
            self._mark_disconnected(reason=err_msg)
            return False

        self._logger.info(f"Authenticating SecureNode '{self.id}' using unique key...")

        # Wrap underlying socket with TLS/SSL if enabled
        if self.use_tls and hasattr(self._board, "sock") and self._board.sock:
            try:
                sock = self._board.sock
                orig_timeout = sock.gettimeout()
                sock.settimeout(3.0)

                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

                self._board.sock = ssl_ctx.wrap_socket(sock, server_hostname=self.host)
                self._board.sock.settimeout(orig_timeout)
                self._logger.info(f"TLS tunnel established for SecureNode '{self.id}'.")
            except Exception as se:
                err_msg = f"TLS_ERROR: Handshake failed/timed out for SecureNode '{self.id}': {se}"
                self._logger.error(err_msg)
                self._logger.error(
                    f"[TLS DIAGNOSTIC HINT] Microcontroller at {self.host}:{self.port} did not complete TLS handshake. "
                    "ESP8266 WiFiServerStream operates on plain TCP with Sysex Node Key Auth. "
                    "Set 'use_tls: false' in system.yaml for standard ESP8266 Firmata WiFi connections."
                )
                self._mark_disconnected(reason=err_msg)
                await self.disconnect()
                return False

        # Send Sysex Authentication Command (0x7E)
        auth_success = await self._send_sysex_auth(self.auth_key)
        if auth_success:
            self._authenticated = True
            self._logger.info(f"SecureNode '{self.id}' authenticated successfully.")
            return True
        else:
            err_msg = f"SECURITY_AUTH_FAILED: Invalid auth_key or no response from SecureNode '{self.id}'."
            self._logger.error(err_msg)
            await self.disconnect()
            self._mark_disconnected(reason=err_msg)
            return False

    async def _send_sysex_auth(self, key: str) -> bool:
        """Encode auth key string into Firmata 7-bit sysex bytes and send to microcontroller."""
        if not self._board:
            return False

        # Encode ASCII string to Firmata 7-bit LSB/MSB byte pairs
        payload = []
        for char in key.encode("utf-8"):
            payload.append(char & 0x7F)
            payload.append((char >> 7) & 0x7F)

        event = asyncio.Event()
        auth_result = False
        loop = asyncio.get_running_loop()

        def _auth_response_cb(data):
            nonlocal auth_result
            if data and len(data) >= 1:
                auth_result = bool(data[0])
            if not loop.is_closed():
                loop.call_soon_threadsafe(event.set)

        try:
            # Register sysex response callback for SYSEX_AUTH_RESPONSE (0x7F) in Pymata4 report_dispatch
            if hasattr(self._board, "report_dispatch"):
                self._board.report_dispatch[SYSEX_AUTH_RESPONSE] = [_auth_response_cb, 0]
            
            # Send SYSEX_AUTH_REQUEST (0x7E)
            if hasattr(self._board, "_send_sysex"):
                self._board._send_sysex(SYSEX_AUTH_REQUEST, payload)

            await asyncio.wait_for(event.wait(), timeout=3.0)
            return auth_result
        except asyncio.TimeoutError:
            self._logger.warning(f"Timeout waiting for auth response from SecureNode '{self.id}'.")
            return False
        except Exception as e:
            self._logger.warning(f"Error during auth handshake for SecureNode '{self.id}': {e}")
            return False
        finally:
            if hasattr(self._board, "report_dispatch"):
                self._board.report_dispatch[SYSEX_AUTH_RESPONSE] = [lambda data: None, 0]

    async def probe_connection(self) -> bool:
        """Active probe delegating to FirmataNode thread-safe socket check."""
        return await super().probe_connection()
