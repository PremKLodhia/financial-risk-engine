import os
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, List
from src.models.base import AbstractRiskModel
from src.core.types import ExtractedFeatures, RiskFactor
from src.core.config import settings

class AutoencoderNet(nn.Module):
    def __init__(self, input_dim: int = 12):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 8),
            nn.LeakyReLU(0.1),
            nn.Linear(8, 4),
            nn.LeakyReLU(0.1),
            nn.Linear(4, 2)  # Bottleneck latent space
        )
        self.decoder = nn.Sequential(
            nn.Linear(2, 4),
            nn.LeakyReLU(0.1),
            nn.Linear(4, 8),
            nn.LeakyReLU(0.1),
            nn.Linear(8, input_dim)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        return self.decoder(latent)

class DeepAutoencoderRiskModel(AbstractRiskModel):
    def __init__(self):
        self.net = AutoencoderNet(input_dim=12)
        self.net.eval()
        self.baseline_mean_loss = 0.15
        self._initialize_weights()

    def _initialize_weights(self):
        torch.manual_seed(42)
        # Synthetic quick pre-training on normal distributions
        X_train = torch.randn(800, 12) * 0.5 + 1.0
        optimizer = torch.optim.Adam(self.net.parameters(), lr=0.01)
        loss_fn = nn.MSELoss()
        
        self.net.train()
        for _ in range(25):
            optimizer.zero_grad()
            out = self.net(X_train)
            loss = loss_fn(out, X_train)
            loss.backward()
            optimizer.step()
        self.net.eval()

    def score(self, features: ExtractedFeatures, vector: np.ndarray) -> Tuple[float, List[RiskFactor]]:
        factors: List[RiskFactor] = []
        with torch.no_grad():
            tensor_in = torch.tensor(vector, dtype=torch.float32).unsqueeze(0)
            reconstructed = self.net(tensor_in)
            mse_loss = float(nn.functional.mse_loss(reconstructed, tensor_in).item())
            
        # Sigmoidal mapping of reconstruction loss
        # Typical loss < 0.2 => low risk; loss > 1.5 => high anomaly
        risk = float(1.0 / (1.0 + np.exp(-2.5 * (mse_loss - 0.75))))
        risk = max(0.01, min(0.99, risk))
        
        if risk > 0.60:
            factors.append(RiskFactor(
                name="NEURAL_RECONSTRUCTION_LOSS_SPIKE",
                impact_score=risk,
                description=f"Deep autoencoder reconstruction error ({mse_loss:.2f}) indicates non-linear pattern anomaly."
            ))
        return risk, factors
