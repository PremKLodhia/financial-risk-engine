import threading
from collections import deque
from datetime import datetime, timezone
import numpy as np
from typing import Dict, List, Set, Tuple
from src.core.types import Transaction, ExtractedFeatures
from src.core.config import settings
from src.features.geo_features import haversine_distance_km, calculate_implied_speed_kmh

LOCK_STRIPES = 64


class StatefulAccountStore:
    """Per-account sliding-window state.

    Uses lock striping: each account maps to one of LOCK_STRIPES locks by hash, so
    transactions for different accounts rarely contend, while all updates for one
    account are serialised. An account always maps to the same stripe, which makes
    the check-then-create of its entries in the shared dicts safe.
    """

    def __init__(self, max_history: int = 500, stripes: int = LOCK_STRIPES):
        self.max_history = max_history
        self._locks = [threading.Lock() for _ in range(stripes)]
        # account_id -> deque of (timestamp, amount, lat, lon, device_id, counterparty_id)
        self.history: Dict[str, deque] = {}
        self.known_devices: Dict[str, Set[str]] = {}
        self.known_counterparties: Dict[str, Set[str]] = {}

    def _lock_for(self, account_id: str) -> threading.Lock:
        return self._locks[hash(account_id) % len(self._locks)]

    def extract_and_update(self, tx: Transaction) -> Tuple[ExtractedFeatures, np.ndarray]:
        with self._lock_for(tx.account_id):
            account = tx.account_id
            now = tx.timestamp
            
            if account not in self.history:
                self.history[account] = deque(maxlen=self.max_history)
                self.known_devices[account] = set()
                self.known_counterparties[account] = set()
            
            hist = self.history[account]
            devices = self.known_devices[account]
            counterparties = self.known_counterparties[account]
            
            # Check novelty before updating state
            is_new_dev = (tx.device_id not in devices) and (len(devices) > 0)
            is_new_cp = (tx.counterparty_id not in counterparties) and (len(counterparties) > 0)
            
            # Compute geo and velocity from the immediate previous transaction
            dist_km = 0.0
            speed_kmh = 0.0
            if len(hist) > 0:
                last_t, last_amt, last_lat, last_lon, _, _ = hist[-1]
                dt = max(0.1, now - last_t)
                dist_km = haversine_distance_km(last_lat, last_lon, tx.latitude, tx.longitude)
                speed_kmh = calculate_implied_speed_kmh(dist_km, dt)
            
            # Sliding time windows
            t_5m = now - settings.WINDOW_VELOCITY_SHORT
            t_1h = now - settings.WINDOW_VELOCITY_MEDIUM
            t_24h = now - settings.WINDOW_VELOCITY_LONG
            
            v_5m = 0
            v_1h = 0
            v_24h = 0
            sum_5m = 0.0
            amounts_24h: List[float] = []
            
            for t_item, amt_item, _, _, _, _ in reversed(hist):
                if t_item >= t_24h:
                    v_24h += 1
                    amounts_24h.append(amt_item)
                    if t_item >= t_1h:
                        v_1h += 1
                    if t_item >= t_5m:
                        v_5m += 1
                        sum_5m += amt_item
                else:
                    break
            
            # Summary statistics
            if len(amounts_24h) > 1:
                mean_24h = float(np.mean(amounts_24h))
                std_24h = float(np.std(amounts_24h))
                std_24h = max(1.0, std_24h)
                z_score = float((tx.amount - mean_24h) / std_24h)
            else:
                mean_24h = tx.amount
                std_24h = 0.0
                z_score = 0.0
            
            dt_obj = datetime.fromtimestamp(now, timezone.utc)
            hour = dt_obj.hour
            is_weekend = dt_obj.weekday() >= 5
            
            # Commit this transaction to history
            hist.append((now, tx.amount, tx.latitude, tx.longitude, tx.device_id, tx.counterparty_id))
            devices.add(tx.device_id)
            counterparties.add(tx.counterparty_id)
            
            extracted = ExtractedFeatures(
                account_id=account,
                amount=tx.amount,
                velocity_5m=v_5m,
                velocity_1h=v_1h,
                velocity_24h=v_24h,
                amount_sum_5m=sum_5m,
                amount_mean_24h=mean_24h,
                amount_std_24h=std_24h,
                amount_z_score=z_score,
                distance_from_last_km=dist_km,
                speed_kmh_from_last=speed_kmh,
                is_new_counterparty=is_new_cp,
                is_new_device=is_new_dev,
                hour_of_day=hour,
                is_weekend=is_weekend
            )
            
            # Vector representation for ML models (12 numeric features)
            norm_vector = np.array([
                np.log1p(tx.amount),
                float(v_5m),
                float(v_1h),
                np.log1p(sum_5m),
                np.log1p(mean_24h),
                z_score,
                np.log1p(dist_km),
                min(2000.0, speed_kmh) / 1000.0,
                1.0 if is_new_cp else 0.0,
                1.0 if is_new_dev else 0.0,
                float(hour) / 24.0,
                1.0 if is_weekend else 0.0
            ], dtype=np.float32)
            
            return extracted, norm_vector

    def clear(self):
        # Take every stripe, always in the same order, so clear() cannot deadlock.
        for lock in self._locks:
            lock.acquire()
        try:
            self.history.clear()
            self.known_devices.clear()
            self.known_counterparties.clear()
        finally:
            for lock in reversed(self._locks):
                lock.release()

global_feature_store = StatefulAccountStore()
