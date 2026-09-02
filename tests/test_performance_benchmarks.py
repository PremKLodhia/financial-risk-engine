import unittest
import time
import numpy as np
from src.models.ensemble import EnsembleRiskScorer
from src.ingestion.stream_simulator import TransactionStreamSimulator

class TestPerformanceBenchmark(unittest.TestCase):
    def test_latency_sla(self):
        scorer = EnsembleRiskScorer()
        sim = TransactionStreamSimulator()
        latencies = []
        num_transactions = 500
        
        # Warm up
        for _ in range(20):
            scorer.evaluate(sim.generate_normal_transaction())
            
        start_all = time.perf_counter()
        for _ in range(num_transactions):
            tx = sim.generate_normal_transaction()
            assessment = scorer.evaluate(tx)
            latencies.append(assessment.latency_ms)
        total_time = time.perf_counter() - start_all
        
        p50 = float(np.percentile(latencies, 50))
        p95 = float(np.percentile(latencies, 95))
        p99 = float(np.percentile(latencies, 99))
        throughput_rps = num_transactions / total_time
        
        print(f"\n--- Benchmark Results ({num_transactions} tx) ---")
        print(f"Throughput:  {throughput_rps:.1f} tx/sec")
        print(f"Latency P50: {p50:.2f} ms")
        print(f"Latency P95: {p95:.2f} ms")
        print(f"Latency P99: {p99:.2f} ms")
        print("------------------------------------------\n")
        
        self.assertLess(p99, 15.0, f"P99 latency ({p99:.2f} ms) exceeded 15ms target")
        self.assertGreater(throughput_rps, 100.0, "Throughput below SLA target")

if __name__ == "__main__":
    unittest.main()
