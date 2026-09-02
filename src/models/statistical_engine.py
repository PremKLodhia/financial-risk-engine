import numpy as np
from typing import Tuple, List
from src.models.base import AbstractRiskModel
from src.core.types import ExtractedFeatures, RiskFactor
from src.core.config import settings

class StatisticalRiskEngine(AbstractRiskModel):
    """Deterministic, rule-and-heuristic based quantitative risk scoring engine."""
    
    def score(self, features: ExtractedFeatures, vector: np.ndarray) -> Tuple[float, List[RiskFactor]]:
        factors: List[RiskFactor] = []
        sub_scores = []
        
        # 1. Z-Score Deviation on Amount
        z = features.amount_z_score
        if z > 4.0:
            sub_scores.append(0.85)
            factors.append(RiskFactor(
                name="EXTREME_AMOUNT_SPIKE",
                impact_score=0.85,
                description=f"Transaction amount is {z:.1f} standard deviations above account mean."
            ))
        elif z > 2.5:
            sub_scores.append(0.55)
            factors.append(RiskFactor(
                name="ELEVATED_AMOUNT",
                impact_score=0.55,
                description=f"Transaction amount deviates significantly (Z={z:.1f}) from typical baseline."
            ))
        else:
            sub_scores.append(0.05)
            
        # 2. Velocity Bursts
        if features.velocity_5m >= 5:
            sub_scores.append(0.90)
            factors.append(RiskFactor(
                name="HIGH_FREQUENCY_VELOCITY_BURST",
                impact_score=0.90,
                description=f"Account initiated {features.velocity_5m} transactions in under 5 minutes."
            ))
        elif features.velocity_1h >= 10:
            sub_scores.append(0.60)
            factors.append(RiskFactor(
                name="ELEVATED_HOURLY_VELOCITY",
                impact_score=0.60,
                description=f"{features.velocity_1h} transactions within 1 hour."
            ))
        else:
            sub_scores.append(0.05)
            
        # 3. Impossible Travel Anomaly
        if features.speed_kmh_from_last > settings.MAX_PLAUSIBLE_SPEED_KMH:
            sub_scores.append(0.95)
            factors.append(RiskFactor(
                name="IMPOSSIBLE_TRAVEL_SPEED",
                impact_score=0.95,
                description=f"Implied physical relocation speed of {features.speed_kmh_from_last:.0f} km/h between logins."
            ))
            
        # 4. Device & Counterparty Novelty Multipliers
        if features.is_new_device and features.amount > 1000.0:
            sub_scores.append(0.70)
            factors.append(RiskFactor(
                name="NEW_DEVICE_HIGH_VALUE",
                impact_score=0.70,
                description=f"High value transaction (£{features.amount:,.2f}) initiated from unrecognized device."
            ))
            
        # 5. Off-Hours High Volume
        if (features.hour_of_day >= 1 and features.hour_of_day <= 5) and features.amount > 2000.0:
            sub_scores.append(0.65)
            factors.append(RiskFactor(
                name="OFF_HOURS_HIGH_VALUE",
                impact_score=0.65,
                description="High value transaction executed during dormant hours (01:00 - 05:00 UTC)."
            ))
            
        final_score = float(np.max(sub_scores) if sub_scores else 0.05)
        # Cap between 0.02 and 0.99
        final_score = max(0.02, min(0.99, final_score))
        return final_score, factors
