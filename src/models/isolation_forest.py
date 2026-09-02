import os
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from typing import Tuple, List
from src.models.base import AbstractRiskModel
from src.core.types import ExtractedFeatures, RiskFactor
from src.core.config import settings

class IsolationForestRiskModel(AbstractRiskModel):
    def __init__(self):
        self.model: IsolationForest = IsolationForest(
            n_estimators=100,
            contamination=0.03,
            max_samples=256,
            random_state=42
        )
        self.is_fitted = False
        self._initialize_or_load()

    def _initialize_or_load(self):
        model_path = settings.ARTIFACTS_DIR / "isolation_forest.joblib"
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                self.is_fitted = True
                return
            except Exception:
                pass
        # Pre-fit on synthetic baseline manifold
        self._fit_default_baseline()

    def _fit_default_baseline(self):
        np.random.seed(42)
        # Normal retail distribution (1000 samples, 12 features)
        baseline = np.random.normal(loc=[3.5, 0.2, 0.8, 4.0, 3.5, 0.0, 1.0, 0.05, 0.1, 0.05, 0.5, 0.2],
                                    scale=[1.2, 0.4, 0.8, 1.5, 1.0, 1.0, 1.5, 0.1, 0.3, 0.2, 0.3, 0.4],
                                    size=(1200, 12)).astype(np.float32)
        self.model.fit(baseline)
        self.is_fitted = True

    def score(self, features: ExtractedFeatures, vector: np.ndarray) -> Tuple[float, List[RiskFactor]]:
        factors: List[RiskFactor] = []
        X = vector.reshape(1, -1)
        # Decision function: lower values indicate higher outlier score
        raw_score = self.model.decision_function(X)[0]
        # Map raw score [-0.5, 0.5] to [0.0, 1.0] risk
        # 0.5 (normal) -> 0.0 risk, -0.5 (outlier) -> 1.0 risk
        normalized_risk = float(1.0 / (1.0 + np.exp(6.0 * raw_score)))
        normalized_risk = max(0.01, min(0.99, normalized_risk))
        
        if normalized_risk > 0.65:
            factors.append(RiskFactor(
                name="MULTI_DIMENSIONAL_DISTRIBUTION_OUTLIER",
                impact_score=normalized_risk,
                description="Transaction vector isolates rapidly in multi-dimensional feature space."
            ))
        return normalized_risk, factors
