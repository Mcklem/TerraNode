import unittest
from automation.rule_engine import RuleEngine
from core.device_manager import DeviceManager
from core.event_bus import EventBus
from core.node_manager import NodeManager
from core.pin_manager import PinManager
from devices.actuators.relay import RelayActuator


class TestRuleEngine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.nm = NodeManager()
        self.pm = PinManager()
        self.dm = DeviceManager(self.nm, self.pm)
        self.bus = EventBus()

        node = self.nm.create_node("n1", {"driver": "mock", "host": "127.0.0.1"})
        await node.connect()

        self.dm.initialize_devices({
            "soil_01": {"type": "soil_moisture", "node": "n1", "pin": "A0"},
            "pump_01": {"type": "relay", "node": "n1", "pin": "D5"},
        })
        await self.dm.start_all()

        rules_cfg = {
            "irrigation_start": {
                "enabled": True,
                "condition": {"device": "soil_01", "property": "value", "operator": "<", "value": 30},
                "actions": [{"device": "pump_01", "command": "turn_on"}],
            }
        }
        self.engine = RuleEngine(rules_cfg, self.dm, self.bus)
        self.engine.start()

    async def test_rule_triggers_actuator_on_condition(self):
        pump: RelayActuator = self.dm.get_device("pump_01")
        self.assertEqual(pump.current_state, "OFF")

        # Publish sensor event with soil moisture = 25 (< 30)
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 25.0, "status": "OK"},
        )

        self.assertEqual(pump.current_state, "ON")

    async def test_rule_edge_triggering_prevents_duplicate_actions(self):
        pump: RelayActuator = self.dm.get_device("pump_01")
        self.assertEqual(pump.current_state, "OFF")

        executed_events = []
        self.bus.subscribe("rule.triggered", lambda evt: executed_events.append(evt))

        # First trigger (< 30) -> Executed
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 25.0, "status": "OK"},
        )
        self.assertEqual(len(executed_events), 1)

        # Second poll while condition remains (< 30) -> Not re-executed
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 22.0, "status": "OK"},
        )
        self.assertEqual(len(executed_events), 1)

        # Condition resets (>= 30)
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 50.0, "status": "OK"},
        )
        self.assertEqual(len(executed_events), 1)

        # Condition matches again (< 30) -> Triggers again!
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 15.0, "status": "OK"},
        )
        self.assertEqual(len(executed_events), 2)

    async def test_rule_does_not_trigger_when_condition_false(self):
        pump: RelayActuator = self.dm.get_device("pump_01")
        self.assertEqual(pump.current_state, "OFF")

        # Publish sensor event with soil moisture = 50 (not < 30)
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 50.0, "status": "OK"},
        )

        self.assertEqual(pump.current_state, "OFF")

    async def test_rule_hysteresis_deadband(self):
        # Configure rule with threshold < 30 and hysteresis 5 (remains active until >= 35)
        self.engine.rules_config["irrigation_start"]["condition"]["hysteresis"] = 5.0

        # 1. Trigger condition with 25 (< 30)
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 25.0, "status": "OK"},
        )
        self.assertTrue(self.engine._rule_states["irrigation_start"])

        # 2. Moisture rises to 32 (above 30, but below 30 + 5 = 35) -> should remain triggered (deadband)
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 32.0, "status": "OK"},
        )
        self.assertTrue(self.engine._rule_states["irrigation_start"])

        # 3. Moisture rises to 36 (>= 35) -> condition resets
        await self.bus.publish(
            "device.value_changed",
            sender="soil_01",
            payload={"id": "soil_01", "value": 36.0, "status": "OK"},
        )
        self.assertFalse(self.engine._rule_states["irrigation_start"])


if __name__ == "__main__":
    unittest.main()
