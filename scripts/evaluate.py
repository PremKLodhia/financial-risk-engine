"""Offline detection evaluation on SYNTHETIC data.

Generates a labelled stream with TransactionStreamSimulator (normal payments mixed
with impossible-travel and velocity-burst attacks), scores every transaction with
the ensemble in stream order, and reports ROC-AUC, precision and recall using
sklearn.metrics.

Labels come from the simulator's transaction ids:
  TX-ATTACK-*  impossible-travel transaction           -> 1
  TX-BURST-*   every transaction in a velocity burst   -> 1
  anything else (normal payments, the legitimate
  coffee purchase before an impossible-travel attack)  -> 0

Precision and recall treat a transaction as flagged when the engine's decision is
anything other than ALLOW (overall score >= THRESHOLD_REVIEW).

These numbers describe the simulator's own attack patterns, not real-world fraud.

Usage:
    python scripts/evaluate.py [--events 5000] [--anomaly-rate 0.08] [--seed 42]
"""
import argparse
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.metrics import precision_score, recall_score, roc_auc_score  # noqa: E402

from src.core.config import settings  # noqa: E402
from src.core.types import DecisionAction  # noqa: E402
from src.features.rolling_windows import global_feature_store  # noqa: E402
from src.ingestion.stream_simulator import TransactionStreamSimulator  # noqa: E402
from src.models.ensemble import EnsembleRiskScorer  # noqa: E402

ATTACK_PREFIXES = ("TX-ATTACK-", "TX-BURST-")


def label_of(transaction_id: str) -> int:
    return 1 if transaction_id.startswith(ATTACK_PREFIXES) else 0


def run_evaluation(events: int = 5000, anomaly_rate: float = 0.08, seed: int = 42) -> dict:
    random.seed(seed)
    global_feature_store.clear()
    scorer = EnsembleRiskScorer()
    stream = TransactionStreamSimulator().stream(anomaly_rate=anomaly_rate)

    labels, scores, flagged = [], [], []
    for tx in itertools.islice(stream, events):
        assessment = scorer.evaluate(tx)
        labels.append(label_of(tx.transaction_id))
        scores.append(assessment.overall_risk_score)
        flagged.append(0 if assessment.decision == DecisionAction.ALLOW else 1)

    return {
        "events": len(labels),
        "positives": sum(labels),
        "negatives": len(labels) - sum(labels),
        "roc_auc": roc_auc_score(labels, scores),
        "precision": precision_score(labels, flagged, zero_division=0),
        "recall": recall_score(labels, flagged, zero_division=0),
        "threshold": settings.THRESHOLD_REVIEW,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--events", type=int, default=5000)
    parser.add_argument("--anomaly-rate", type=float, default=0.08)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    r = run_evaluation(args.events, args.anomaly_rate, args.seed)
    print("Synthetic evaluation (TransactionStreamSimulator, not real data)")
    print(f"events={r['events']} attacks={r['positives']} normal={r['negatives']} "
          f"anomaly_rate={args.anomaly_rate} seed={args.seed}")
    print(f"ROC-AUC:   {r['roc_auc']:.4f}")
    print(f"Precision: {r['precision']:.4f}  (flagged = decision != ALLOW, score >= {r['threshold']:.2f})")
    print(f"Recall:    {r['recall']:.4f}")


if __name__ == "__main__":
    main()
