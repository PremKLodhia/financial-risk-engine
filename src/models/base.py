from abc import ABC, abstractmethod
from typing import Tuple, List
import numpy as np
from src.core.types import ExtractedFeatures, RiskFactor

class AbstractRiskModel(ABC):
    @abstractmethod
    def score(self, features: ExtractedFeatures, vector: np.ndarray) -> Tuple[float, List[RiskFactor]]:
        """Returns normalized risk score in [0.0, 1.0] and contributing factors."""
        pass
