import unittest
import time
from src.core.types import Transaction, TransactionType, DecisionAction
from src.models.ensemble import EnsembleRiskScorer

class TestRiskModels(unittest.TestCase):
    def setUp(self):
        self.scorer = EnsembleRiskScorer()

    def test_ensemble_normal_transaction_allowed(self):
        tx = Transaction(
            transaction_id="TX-NORM",
            account_id="ACC-BENIGN",
            counterparty_id="CP-GROCERY",
            amount=24.50,
            timestamp=time.time(),
            latitude=51.5074,
            longitude=-0.1278,
            device_id="DEV-IPHONE"
        )
        assessment = self.scorer.evaluate(tx)
        self.assertLess(assessment.overall_risk_score, 0.50)
        self.assertEqual(assessment.decision, DecisionAction.ALLOW)
        self.assertLess(assessment.latency_ms, 20.0)

    def test_impossible_travel_blocked(self):
        acc = "ACC-TARGET"
        t0 = time.time()
        
        # Login in London
        tx1 = Transaction(
            transaction_id="TX-LND",
            account_id=acc,
            counterparty_id="CP-1",
            amount=10.0,
            timestamp=t0 - 120,
            latitude=51.5074,
            longitude=-0.1278,
            device_id="DEV-1"
        )
        self.scorer.evaluate(tx1)
        
        # Login in Tokyo 2 minutes later for £3,000
        tx2 = Transaction(
            transaction_id="TX-TOK",
            account_id=acc,
            counterparty_id="CP-CRYPTO",
            amount=3000.0,
            timestamp=t0,
            latitude=35.6762,
            longitude=139.6503,
            device_id="DEV-2"
        )
        assessment2 = self.scorer.evaluate(tx2)
        self.assertGreaterEqual(assessment2.overall_risk_score, 0.85)
        self.assertEqual(assessment2.decision, DecisionAction.BLOCK)
        factor_names = [f.name for f in assessment2.top_risk_factors]
        self.assertTrue(any("IMPOSSIBLE_TRAVEL" in fn for fn in factor_names))

if __name__ == "__main__":
    unittest.main()
