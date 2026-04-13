"""Calibrated baseline risk model (logistic regression on tabular features)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.contracts.features import FeatureVector

FEATURE_NAMES: List[str] = [
    "orders_7d",
    "orders_28d",
    "gmv_28d",
    "orders_wow_change",
    "gmv_mom_change",
    "login_days_28d",
    "support_tickets_28d",
    "config_error_rate_28d",
    "menu_sync_failures_28d",
    "hours_zero_days_28d",
    "peer_gmv_percentile",
]


def feature_names() -> List[str]:
    return list(FEATURE_NAMES)


def vector_to_array(fv: FeatureVector) -> np.ndarray:
    return np.array([[getattr(fv, name) for name in FEATURE_NAMES]], dtype=np.float64)


class BaselineChurnModel:
    """Binary churn risk + multi-class churn type auxiliary head (simplified: type from risk decomposition)."""

    def __init__(self, model_dir: str | None = None) -> None:
        self._model_dir = model_dir or os.environ.get(
            "CHURN_MODEL_DIR",
            str(Path(__file__).resolve().parent / "artifacts"),
        )
        self._clf: CalibratedClassifierCV | None = None
        self._scaler = StandardScaler()
        self._load_or_init()

    def _load_or_init(self) -> None:
        path = Path(self._model_dir) / "baseline.joblib"
        if path.exists():
            try:
                import joblib

                bundle = joblib.load(path)
                self._clf = bundle["clf"]
                self._scaler = bundle["scaler"]
                return
            except Exception:
                pass
        base = LogisticRegression(max_iter=200, class_weight="balanced", random_state=42)
        self._clf = CalibratedClassifierCV(base, cv=3)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        Xs = self._scaler.fit_transform(X)
        self._clf.fit(Xs, y)

    def save(self) -> None:
        import joblib

        Path(self._model_dir).mkdir(parents=True, exist_ok=True)
        path = Path(self._model_dir) / "baseline.joblib"
        joblib.dump({"clf": self._clf, "scaler": self._scaler}, path)

    def predict_proba_churn(self, fv: FeatureVector) -> float:
        path = Path(self._model_dir) / "baseline.joblib"
        if not path.is_file():
            # No trained artifact: use heuristic so demo / tiered features show a real risk spread.
            return float(_heuristic_risk(fv))
        if self._clf is None:
            return float(_heuristic_risk(fv))
        X = vector_to_array(fv)
        Xs = self._scaler.transform(X)
        proba = self._clf.predict_proba(Xs)[0, 1]
        return float(np.clip(proba, 0.0, 1.0))

    def churn_type_probs(self, fv: FeatureVector, risk: float) -> Dict[str, float]:
        """Heuristic mixture conditioned on features + risk (no separate head until trained)."""
        f = fv
        hard = risk * min(1.0, 0.2 + 0.01 * max(0, -f.orders_wow_change))
        soft = risk * min(1.0, 0.3 + 0.005 * max(0, f.support_tickets_28d))
        op = risk * min(1.0, 0.25 + 0.05 * f.hours_zero_days_28d + 0.02 * f.menu_sync_failures_28d)
        s = hard + soft + op + 1e-6
        return {
            "hard": float(hard / s * risk / max(risk, 1e-6)),
            "soft": float(soft / s * risk / max(risk, 1e-6)),
            "operational": float(op / s * risk / max(risk, 1e-6)),
        }


def _heuristic_risk(fv: FeatureVector) -> float:
    """Rule-based risk when no trained model exists."""
    score = 0.35
    if fv.orders_wow_change < -0.15:
        score += 0.2
    if fv.gmv_mom_change < -0.2:
        score += 0.15
    if fv.config_error_rate_28d > 0.1 or fv.menu_sync_failures_28d > 5:
        score += 0.15
    if fv.hours_zero_days_28d > 3:
        score += 0.1
    if fv.login_days_28d < 4:
        score += 0.1
    if fv.peer_gmv_percentile < 25:
        score += 0.1
    return float(np.clip(score, 0.0, 1.0))


def train_from_synthetic_labels(model_dir: str | None = None) -> BaselineChurnModel:
    """Fit a small synthetic dataset so predict_proba works out of the box."""
    rng = np.random.default_rng(42)
    n = 400
    X = rng.normal(size=(n, len(FEATURE_NAMES)))
    # Synthetic churn: low orders, negative wow, high config errors
    y = (
        (X[:, 0] + X[:, 3] * 2 + X[:, 7] * 3 + rng.normal(0, 0.5, n)) > 0.5
    ).astype(int)
    m = BaselineChurnModel(model_dir=model_dir)
    assert m._clf is not None
    m.fit(X, y)
    return m
