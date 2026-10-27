import time
from typing import Dict, List
from src.core.types import (
    Transaction, RiskAssessment, RiskLevel, DecisionAction, RiskFactor
)
from src.core.config import settings
from src.features.rolling_windows import global_feature_store
from src.models.statistical_engine import StatisticalRiskEngine
from src.models.isolation_forest import IsolationForestRiskModel
from src.models.autoencoder import DeepAutoencoderRiskModel

class EnsembleRiskScorer:
    def __init__(self):
        self.statistical_model = StatisticalRiskEngine()
        self.isolation_forest = IsolationForestRiskModel()
        self.autoencoder = DeepAutoencoderRiskModel()

    def evaluate(self, tx: Transaction) -> RiskAssessment:
        t0 = time.perf_counter()
        
        # 1. Feature Extraction (< 1ms)
        extracted, vector = global_feature_store.extract_and_update(tx)
        
        # 2. Sequential inference: each model scores in turn
        stat_score, stat_factors = self.statistical_model.score(extracted, vector)
        if_score, if_factors = self.isolation_forest.score(extracted, vector)
        ae_score, ae_factors = self.autoencoder.score(extracted, vector)
        
        # 3. Weighted Aggregation
        overall_score = (
            settings.WEIGHT_STATISTICAL * stat_score +
            settings.WEIGHT_ISOLATION_FOREST * if_score +
            settings.WEIGHT_AUTOENCODER * ae_score
        )
        
        # Rule Overrides for Critical Hard Failures
        if extracted.speed_kmh_from_last > 1000.0 and tx.amount > 500.0:
            overall_score = max(0.92, overall_score)
        if extracted.velocity_5m >= 7:
            overall_score = max(0.88, overall_score)
            
        overall_score = max(0.01, min(0.99, float(overall_score)))
        
        # 4. Decision Mapping
        if overall_score >= settings.THRESHOLD_BLOCK:
            risk_level = RiskLevel.CRITICAL
            decision = DecisionAction.BLOCK
        elif overall_score >= settings.THRESHOLD_CHALLENGE:
            risk_level = RiskLevel.HIGH
            decision = DecisionAction.CHALLENGE_2FA
        elif overall_score >= settings.THRESHOLD_REVIEW:
            risk_level = RiskLevel.MEDIUM
            decision = DecisionAction.REVIEW
        else:
            risk_level = RiskLevel.LOW
            decision = DecisionAction.ALLOW
            
        # Combine and sort risk factors
        all_factors: List[RiskFactor] = stat_factors + if_factors + ae_factors
        all_factors.sort(key=lambda x: x.impact_score, reverse=True)
        # Deduplicate top factors
        seen = set()
        top_factors = []
        for f in all_factors:
            if f.name not in seen:
                seen.add(f.name)
                top_factors.append(f)
                if len(top_factors) >= 3:
                    break
                    
        latency_ms = (time.perf_counter() - t0) * 1000.0
        
        return RiskAssessment(
            transaction_id=tx.transaction_id,
            timestamp=tx.timestamp,
            overall_risk_score=round(overall_score, 4),
            risk_level=risk_level,
            decision=decision,
            model_breakdown={
                "statistical": round(stat_score, 4),
                "isolation_forest": round(if_score, 4),
                "autoencoder": round(ae_score, 4)
            },
            top_risk_factors=top_factors,
            latency_ms=round(latency_ms, 2)
        )

global_risk_scorer = EnsembleRiskScorer()
