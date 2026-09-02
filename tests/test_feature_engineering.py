import unittest
import time
from src.core.types import Transaction, TransactionType
from src.features.geo_features import haversine_distance_km, calculate_implied_speed_kmh
from src.features.rolling_windows import StatefulAccountStore

class TestFeatureEngineering(unittest.TestCase):
    def test_haversine_distance(self):
        # London (51.5074, -0.1278) to Birmingham (52.4862, -1.8904) ~ 160-170 km
        d = haversine_distance_km(51.5074, -0.1278, 52.4862, -1.8904)
        self.assertTrue(150.0 < d < 180.0, f"Distance {d} out of expected range")

    def test_implied_speed(self):
        # 200 km in 30 minutes (0.5 hours) = 400 km/h
        speed = calculate_implied_speed_kmh(200.0, 1800.0)
        self.assertAlmostEqual(speed, 400.0, places=1)

    def test_rolling_window_velocity_and_zscore(self):
        store = StatefulAccountStore()
        acc = "ACC-TEST-1"
        now = time.time()
        
        # 1. First transaction
        tx1 = Transaction(
            transaction_id="TX-1",
            account_id=acc,
            counterparty_id="CP-1",
            amount=100.0,
            timestamp=now - 200,
            latitude=51.5,
            longitude=-0.1,
            device_id="DEV-A"
        )
        f1, v1 = store.extract_and_update(tx1)
        self.assertEqual(f1.velocity_5m, 0)
        self.assertFalse(f1.is_new_counterparty)
        
        # 2. Second transaction in 2 minutes
        tx2 = Transaction(
            transaction_id="TX-2",
            account_id=acc,
            counterparty_id="CP-2",
            amount=100.0,
            timestamp=now - 80,
            latitude=51.5,
            longitude=-0.1,
            device_id="DEV-A"
        )
        f2, v2 = store.extract_and_update(tx2)
        self.assertEqual(f2.velocity_5m, 1)
        self.assertTrue(f2.is_new_counterparty)

if __name__ == "__main__":
    unittest.main()
