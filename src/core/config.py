from dataclasses import dataclass
from pathlib import Path
import os

@dataclass(frozen=True)
class Settings:
    APP_NAME: str = "Sentinel Financial Risk & Anomaly Detection Engine"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("RISK_ENGINE_ENVIRONMENT", "production")
    
    # Risk Decision Thresholds
    THRESHOLD_REVIEW: float = float(os.getenv("RISK_ENGINE_THRESHOLD_REVIEW", "0.50"))
    THRESHOLD_CHALLENGE: float = float(os.getenv("RISK_ENGINE_THRESHOLD_CHALLENGE", "0.70"))
    THRESHOLD_BLOCK: float = float(os.getenv("RISK_ENGINE_THRESHOLD_BLOCK", "0.85"))
    
    # Time Windows (seconds)
    WINDOW_VELOCITY_SHORT: int = int(os.getenv("RISK_ENGINE_WINDOW_SHORT", "300"))      # 5 minutes
    WINDOW_VELOCITY_MEDIUM: int = int(os.getenv("RISK_ENGINE_WINDOW_MEDIUM", "3600"))   # 1 hour
    WINDOW_VELOCITY_LONG: int = int(os.getenv("RISK_ENGINE_WINDOW_LONG", "86400"))      # 24 hours
    MAX_ACCOUNT_HISTORY: int = 1000
    
    # Geo Anomaly Constraints
    MAX_PLAUSIBLE_SPEED_KMH: float = 900.0  # Commercial flight upper limit
    
    # Model Weights in Ensemble
    WEIGHT_STATISTICAL: float = 0.35
    WEIGHT_ISOLATION_FOREST: float = 0.35
    WEIGHT_AUTOENCODER: float = 0.30
    
    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"

settings = Settings()
