import sys
import threading
import time

from src.core.types import Transaction
from src.features.rolling_windows import LOCK_STRIPES, StatefulAccountStore

ACCOUNTS = [f"ACC-{i}" for i in range(12)]
THREADS = 16
TX_PER_ACCOUNT_PER_THREAD = 20  # 16 * 20 = 320 per account, within max_history


def test_each_account_always_uses_the_same_stripe():
    store = StatefulAccountStore()
    assert len(store._locks) == LOCK_STRIPES
    assert store._lock_for("ACC-1") is store._lock_for("ACC-1")
    distinct = {id(store._lock_for(f"ACC-{i}")) for i in range(500)}
    assert len(distinct) > 1


def test_velocity_counts_stay_correct_under_concurrency():
    store = StatefulAccountStore(max_history=1000)
    now = time.time()
    seen = {acc: [] for acc in ACCOUNTS}
    seen_lock = threading.Lock()
    barrier = threading.Barrier(THREADS)
    errors = []

    def worker(worker_id: int):
        try:
            barrier.wait()
            for n in range(TX_PER_ACCOUNT_PER_THREAD):
                # Interleave overlapping accounts across all threads.
                for acc in ACCOUNTS:
                    tx = Transaction(
                        transaction_id=f"TX-{worker_id}-{n}-{acc}",
                        account_id=acc,
                        counterparty_id="MERCH-1",
                        amount=10.0,
                        timestamp=now,
                        latitude=51.5,
                        longitude=-0.12,
                        device_id="DEV-1",
                    )
                    features, _ = store.extract_and_update(tx)
                    with seen_lock:
                        seen[acc].append(features.velocity_5m)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    # Switch threads as often as possible so an unlocked read-modify-write would interleave.
    previous = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        sys.setswitchinterval(previous)

    assert not errors
    expected = THREADS * TX_PER_ACCOUNT_PER_THREAD
    for acc in ACCOUNTS:
        # Every transaction saw a distinct prior count: no lost or double-counted updates.
        assert sorted(seen[acc]) == list(range(expected)), acc
        assert len(store.history[acc]) == expected


def test_clear_empties_all_state():
    store = StatefulAccountStore()
    for acc in ACCOUNTS:
        store.extract_and_update(Transaction(
            transaction_id=f"TX-{acc}", account_id=acc, counterparty_id="M", amount=1.0,
            timestamp=time.time(), latitude=0.0, longitude=0.0, device_id="D",
        ))
    store.clear()
    assert store.history == {} and store.known_devices == {} and store.known_counterparties == {}
