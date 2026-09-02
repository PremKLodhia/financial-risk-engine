from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from typing import List
import time
from collections import deque
import numpy as np

from src.core.config import settings
from src.core.types import Transaction, RiskAssessment
from src.models.ensemble import global_risk_scorer
from src.ingestion.stream_simulator import TransactionStreamSimulator

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Production-grade real-time financial risk and anomaly detection microservice."
)

# CORS Policy - Restricted methods and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)

# Security Response Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Operational Metrics in Memory
metrics_latencies = deque(maxlen=2000)
metrics_assessments = deque(maxlen=100)
simulator = TransactionStreamSimulator()

@app.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "timestamp": time.time()
    }

@app.post("/v1/score", response_model=RiskAssessment)
def score_transaction(tx: Transaction):
    try:
        assessment = global_risk_scorer.evaluate(tx)
        metrics_latencies.append(assessment.latency_ms)
        metrics_assessments.append(assessment)
        return assessment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/batch-score", response_model=List[RiskAssessment])
def score_batch(transactions: List[Transaction]):
    results = []
    for tx in transactions:
        results.append(global_risk_scorer.evaluate(tx))
    return results

@app.get("/v1/metrics")
def get_metrics():
    lats = list(metrics_latencies)
    if not lats:
        p50, p95, p99 = 0.0, 0.0, 0.0
    else:
        p50 = float(np.percentile(lats, 50))
        p95 = float(np.percentile(lats, 95))
        p99 = float(np.percentile(lats, 99))
        
    recent = list(metrics_assessments)
    anomaly_count = sum(1 for a in recent if a.decision != "ALLOW")
    anomaly_rate = (anomaly_count / max(1, len(recent))) * 100.0
    
    return {
        "total_scored_window": len(lats),
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2),
        "anomaly_rate_percent": round(anomaly_rate, 2),
        "recent_alerts": [a for a in recent if a.decision != "ALLOW"][-10:]
    }

@app.get("/v1/simulate-next", response_model=RiskAssessment)
def simulate_and_score(anomaly_type: str = "random"):
    if anomaly_type == "impossible_travel":
        txs = simulator.generate_impossible_travel_attack()
        global_risk_scorer.evaluate(txs[0])
        assessment = global_risk_scorer.evaluate(txs[1])
    elif anomaly_type == "velocity_burst":
        txs = simulator.generate_velocity_burst_attack()
        assessment = None
        for tx in txs:
            assessment = global_risk_scorer.evaluate(tx)
    else:
        tx = simulator.generate_normal_transaction()
        assessment = global_risk_scorer.evaluate(tx)
        
    metrics_latencies.append(assessment.latency_ms)
    metrics_assessments.append(assessment)
    return assessment

# Load dashboard
@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    dashboard_path = settings.BASE_DIR / "dashboard" / "index.html"
    if dashboard_path.exists():
        with open(dashboard_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Sentinel Risk Engine API Active. Access /docs for Swagger.</h1>"
