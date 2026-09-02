import random
import time
import uuid
from typing import Generator
from src.core.types import Transaction, TransactionType

# Coordinates for major financial hubs
LOCATIONS = {
    "London_UK": (51.5074, -0.1278),
    "Birmingham_UK": (52.4862, -1.8904),
    "Manchester_UK": (53.4808, -2.2426),
    "NewYork_US": (40.7128, -74.0060),
    "Tokyo_JP": (35.6762, 139.6503),
    "Singapore_SG": (1.3521, 103.8198),
    "Frankfurt_DE": (50.1109, 8.6821)
}

class TransactionStreamSimulator:
    def __init__(self, legitimate_account_pool_size: int = 100):
        self.accounts = [f"ACC-{1000 + i}" for i in range(legitimate_account_pool_size)]
        self.devices = {acc: [f"DEV-{uuid.uuid4().hex[:6]}"] for acc in self.accounts}
        self.counterparties = [f"MERCH-{uuid.uuid4().hex[:6]}" for _ in range(50)]

    def generate_normal_transaction(self, base_time: float = None) -> Transaction:
        acc = random.choice(self.accounts)
        dev = random.choice(self.devices[acc])
        cp = random.choice(self.counterparties)
        amount = round(random.lognormvariate(3.2, 0.8), 2)  # Typically £10 - £120
        amount = max(2.50, min(850.0, amount))
        
        city = random.choice(["London_UK", "Birmingham_UK", "Manchester_UK"])
        lat, lon = LOCATIONS[city]
        # Jitter coordinates slightly
        lat += random.uniform(-0.05, 0.05)
        lon += random.uniform(-0.05, 0.05)
        
        return Transaction(
            transaction_id=f"TX-{uuid.uuid4().hex[:10].upper()}",
            account_id=acc,
            counterparty_id=cp,
            amount=amount,
            currency="GBP",
            timestamp=base_time or time.time(),
            transaction_type=TransactionType.PAYMENT,
            latitude=round(lat, 4),
            longitude=round(lon, 4),
            device_id=dev,
            ip_address=f"192.168.1.{random.randint(2, 254)}"
        )

    def generate_impossible_travel_attack(self) -> list[Transaction]:
        """Generates a legitimate transaction in London followed 2 minutes later by a Tokyo transaction."""
        acc = random.choice(self.accounts)
        t0 = time.time() - 120
        tx1 = Transaction(
            transaction_id=f"TX-LEGIT-{uuid.uuid4().hex[:6].upper()}",
            account_id=acc,
            counterparty_id="MERCH-LOCAL-COFFEE",
            amount=4.50,
            timestamp=t0,
            latitude=LOCATIONS["London_UK"][0],
            longitude=LOCATIONS["London_UK"][1],
            device_id=self.devices[acc][0]
        )
        tx2 = Transaction(
            transaction_id=f"TX-ATTACK-{uuid.uuid4().hex[:6].upper()}",
            account_id=acc,
            counterparty_id="CRYPTO-EXCHANGE-GLOBAL",
            amount=3850.00,
            timestamp=t0 + 120,
            transaction_type=TransactionType.TRANSFER,
            latitude=LOCATIONS["Tokyo_JP"][0],
            longitude=LOCATIONS["Tokyo_JP"][1],
            device_id=f"DEV-UNKNOWN-{uuid.uuid4().hex[:6]}"
        )
        return [tx1, tx2]

    def generate_velocity_burst_attack(self) -> list[Transaction]:
        """Generates 8 rapid transactions in 30 seconds (card testing pattern)."""
        acc = random.choice(self.accounts)
        dev = f"DEV-BOT-{uuid.uuid4().hex[:4]}"
        t0 = time.time() - 30
        txs = []
        for i in range(8):
            txs.append(Transaction(
                transaction_id=f"TX-BURST-{i}-{uuid.uuid4().hex[:4].upper()}",
                account_id=acc,
                counterparty_id=f"MERCH-ONLINE-{i}",
                amount=round(random.uniform(1.0, 5.0), 2),
                timestamp=t0 + (i * 4),
                latitude=LOCATIONS["Frankfurt_DE"][0],
                longitude=LOCATIONS["Frankfurt_DE"][1],
                device_id=dev
            ))
        return txs

    def stream(self, anomaly_rate: float = 0.08) -> Generator[Transaction, None, None]:
        while True:
            r = random.random()
            if r < anomaly_rate / 2:
                for tx in self.generate_impossible_travel_attack():
                    yield tx
            elif r < anomaly_rate:
                for tx in self.generate_velocity_burst_attack():
                    yield tx
            else:
                yield self.generate_normal_transaction()
