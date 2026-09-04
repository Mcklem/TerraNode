import unittest
from unittest.mock import MagicMock, patch
import asyncio

from nodes.secure_firmata_node import SecureFirmataNode
from core.node_manager import NodeManager


class TestSecureFirmataNode(unittest.TestCase):
    def test_node_manager_creates_secure_firmata_node(self):
        mgr = NodeManager()
        cfg = {
            "driver": "secure_standard_firmata_wifi",
            "host": "192.168.1.100",
            "port": 3030,
            "auth_key": "test_secret_key_123",
            "use_tls": False,
            "enabled": True,
        }
        node = mgr.create_node("secure_node_01", cfg)
        self.assertIsInstance(node, SecureFirmataNode)
        self.assertEqual(node.auth_key, "test_secret_key_123")
        self.assertFalse(node.use_tls)

    def test_secure_firmata_node_initialization(self):
        node = SecureFirmataNode(
            node_id="sec_01",
            driver="secure_standard_firmata_wifi",
            host="192.168.1.150",
            port=3030,
            auth_key="my_key",
        )
        self.assertEqual(node.id, "sec_01")
        self.assertEqual(node.auth_key, "my_key")
        self.assertFalse(node._authenticated)


if __name__ == "__main__":
    unittest.main()
