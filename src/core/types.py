from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
import time

class TransactionType(str, Enum):
    PAYMENT = "PAYMENT"
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"
    REFUND = "REFUND"
    CRYPTO_PURCHASE = "CRYPTO_PURCHASE"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class DecisionAction(str, Enum):
    ALLOW = "ALLOW"
    REVIEW = "REVIEW"
    CHALLENGE_2FA = "CHALLENGE_2FA"
    BLOCK = "BLOCK"

class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    counterparty_id: str
    amount: float = Field(gt=0, description="Transaction amount in GBP")
    currency: str = "GBP"
    timestamp: float = Field(default_factory=time.time, description="Epoch timestamp in seconds")
    transaction_type: TransactionType = TransactionType.PAYMENT
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    device_id: str
    ip_address: str = "127.0.0.1"

class ExtractedFeatures(BaseModel):
    account_id: str
    amount: float
    velocity_5m: int
    velocity_1h: int
    velocity_24h: int
    amount_sum_5m: float
    amount_mean_24h: float
    amount_std_24h: float
    amount_z_score: float
    distance_from_last_km: float
    speed_kmh_from_last: float
    is_new_counterparty: bool
    is_new_device: bool
    hour_of_day: int
    is_weekend: bool

class RiskFactor(BaseModel):
    name: str
    impact_score: float
    description: str

class RiskAssessment(BaseModel):
    transaction_id: str
    timestamp: float
    overall_risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    decision: DecisionAction
    model_breakdown: Dict[str, float]
    top_risk_factors: List[RiskFactor]
    latency_ms: float
