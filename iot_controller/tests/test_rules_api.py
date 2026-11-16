import unittest
from fastapi.testclient import TestClient
from api.app import create_app
from api.dependencies import system_container


class MockRuleEngine:
    def __init__(self):
        self.rules_config = {
            "irrigation_start": {
                "enabled": True,
                "condition": {
                    "device": "light_01",
                    "property": "value",
                    "operator": "<",
                    "value": 400
                },
                "actions": [
                    {
                        "device": "irrigation_pump",
                        "command": "turn_on",
                        "args": {}
                    }
                ],
                "retrigger": False
            },
            "frost_alert": {
                "enabled": True,
                "condition": {
                    "device": "environment_01",
                    "property": "temperature",
                    "operator": "<",
                    "value": -10
                },
                "actions": [
                    {
                        "type": "notification",
                        "channel": "telegram",
                        "title": "Alerta de Helada",
                        "message": "Temperatura crítica {value}°C"
                    }
                ],
                "retrigger": False,
                "cooldown": 86400,
                "recovery_message": "Fin de riesgo por helada"
            }
        }
        self._triggered_calls = []

    def get_rule_states(self):
        return [
            {
                "id": "irrigation_start",
                "enabled": self.rules_config["irrigation_start"]["enabled"],
                "condition": self.rules_config["irrigation_start"]["condition"],
                "actions": self.rules_config["irrigation_start"]["actions"],
                "retrigger": False,
                "is_triggered": True,
                "last_sensor_value": 312
            },
            {
                "id": "frost_alert",
                "enabled": self.rules_config["frost_alert"]["enabled"],
                "condition": self.rules_config["frost_alert"]["condition"],
                "actions": self.rules_config["frost_alert"]["actions"],
                "retrigger": False,
                "cooldown": 86400,
                "recovery_message": "Fin de riesgo por helada",
                "is_triggered": False,
                "last_sensor_value": -12
            }
        ]

    def toggle_rule(self, rule_id: str):
        if rule_id not in self.rules_config:
            return None
        cfg = self.rules_config[rule_id]
        cfg["enabled"] = not cfg.get("enabled", True)
        return cfg["enabled"]


class TestRulesAPI(unittest.TestCase):
    def setUp(self):
        self.mock_rule_engine = MockRuleEngine()
        system_container.rule_engine = self.mock_rule_engine
        self.app = create_app()
        self.client = TestClient(self.app)

    def test_list_rules(self):
        response = self.client.get("/api/v1/rules")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], "irrigation_start")
        self.assertEqual(data[0]["is_triggered"], True)
        self.assertEqual(data[0]["last_sensor_value"], 312)

        # Test notification rule in list
        frost = data[1]
        self.assertEqual(frost["id"], "frost_alert")
        self.assertEqual(frost["cooldown"], 86400)
        self.assertEqual(frost["recovery_message"], "Fin de riesgo por helada")
        self.assertEqual(len(frost["actions"]), 1)
        self.assertEqual(frost["actions"][0]["type"], "notification")
        self.assertEqual(frost["actions"][0]["channel"], "telegram")

    def test_get_rule_detail(self):
        response = self.client.get("/api/v1/rules/irrigation_start")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["id"], "irrigation_start")
        self.assertEqual(data["condition"]["device"], "light_01")

        # Test notification rule detail
        resp_frost = self.client.get("/api/v1/rules/frost_alert")
        self.assertEqual(resp_frost.status_code, 200)
        data_frost = resp_frost.json()
        self.assertEqual(data_frost["id"], "frost_alert")
        self.assertEqual(data_frost["actions"][0]["channel"], "telegram")

        response_404 = self.client.get("/api/v1/rules/non_existent_rule")
        self.assertEqual(response_404.status_code, 404)

    def test_toggle_rule(self):
        response = self.client.post("/api/v1/rules/irrigation_start/toggle")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["enabled"])

        # Toggle back
        response_back = self.client.post("/api/v1/rules/irrigation_start/toggle")
        self.assertEqual(response_back.status_code, 200)
        self.assertTrue(response_back.json()["enabled"])


if __name__ == "__main__":
    unittest.main()
