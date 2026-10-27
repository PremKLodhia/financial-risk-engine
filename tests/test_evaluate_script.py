from scripts.evaluate import label_of, run_evaluation


def test_labels_follow_simulator_ids():
    assert label_of("TX-ATTACK-ABC123") == 1
    assert label_of("TX-BURST-3-ABCD") == 1
    assert label_of("TX-LEGIT-ABC123") == 0
    assert label_of("TX-0123456789") == 0


def test_run_evaluation_reports_metrics_for_both_classes():
    result = run_evaluation(events=300, anomaly_rate=0.2, seed=7)

    assert result["events"] == 300
    assert result["positives"] > 0 and result["negatives"] > 0
    for key in ("roc_auc", "precision", "recall"):
        assert 0.0 <= result[key] <= 1.0
