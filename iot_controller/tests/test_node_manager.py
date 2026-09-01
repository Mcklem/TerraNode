import unittest
from core.node_manager import NodeManager
from nodes.mock_node import MockNode


class TestNodeManager(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.nm = NodeManager()

    async def test_create_and_connect_mock_node(self):
        node_cfg = {"driver": "mock", "host": "127.0.0.1", "port": 3030, "enabled": True}
        node = self.nm.create_node("test_node", node_cfg)
        self.assertIsInstance(node, MockNode)

        await self.nm.connect_all()
        self.assertTrue(node.is_connected())

        health = node.health()
        self.assertEqual(health["status"], "CONNECTED")

        await self.nm.disconnect_all()
        self.assertFalse(node.is_connected())


if __name__ == "__main__":
    unittest.main()
