import unittest
from fastapi.testclient import TestClient
from src.api.app import app

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "HEALTHY")

    def test_score_endpoint(self):
        payload = {
            "transaction_id": "TX-API-TEST",
            "account_id": "ACC-999",
            "counterparty_id": "CP-999",
            "amount": 45.0,
            "currency": "GBP",
            "timestamp": 1725270000.0,
            "transaction_type": "PAYMENT",
            "latitude": 51.5,
            "longitude": -0.12,
            "device_id": "DEV-TEST",
            "ip_address": "127.0.0.1"
        }
        res = self.client.post("/v1/score", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("overall_risk_score", data)
        self.assertIn("decision", data)
        self.assertLess(data["latency_ms"], 30.0)

    def test_metrics_endpoint(self):
        res = self.client.get("/v1/metrics")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("latency_p50_ms", data)

if __name__ == "__main__":
    unittest.main()
