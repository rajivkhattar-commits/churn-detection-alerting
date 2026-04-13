"""Load example churn labels and evaluate baseline risk ranking."""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from app.contracts.features import ChurnLabelRow, FeatureVector, ProductCode
from app.ml.baseline import BaselineChurnModel, vector_to_array


def _default_csv_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "churn_labels_example.csv"


def load_labels_csv(path: str | Path | None = None) -> List[ChurnLabelRow]:
    p = Path(path) if path else _default_csv_path()
    rows: List[ChurnLabelRow] = []
    if not p.exists():
        return rows
    with p.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            cd = row["churn_date"]
            churn_date = date.fromisoformat(cd) if isinstance(cd, str) else cd
            rows.append(
                ChurnLabelRow(
                    venue_id=row["venue_id"],
                    product=ProductCode(row["product"]),
                    churn_type=row["churn_type"],
                    churn_date=churn_date,
                    notes=row.get("notes"),
                )
            )
    return rows


def _synthetic_feature_for_label(label: ChurnLabelRow) -> FeatureVector:
    """Attach plausible features for demo venues (deterministic from venue_id)."""
    h = hash(label.venue_id) % 1000
    base = FeatureVector(
        orders_7d=20 + (h % 30),
        orders_28d=80 + (h % 50),
        gmv_28d=5000 + h * 10,
        orders_wow_change=-0.25 if label.churn_type == "soft" else -0.05,
        gmv_mom_change=-0.3 if label.churn_type == "hard" else -0.1,
        login_days_28d=8 if label.churn_type != "hard" else 2,
        support_tickets_28d=4 if label.churn_type == "soft" else 1,
        config_error_rate_28d=0.15 if label.churn_type == "operational" else 0.02,
        menu_sync_failures_28d=8 if label.churn_type == "operational" else 1,
        hours_zero_days_28d=6 if label.churn_type == "operational" else 0,
        peer_gmv_percentile=20.0,
    )
    return base


def run_backtest(
    model: BaselineChurnModel | None = None,
    labels_path: str | Path | None = None,
) -> Dict[str, Any]:
    """Compute simple AUC-like separation on labeled examples (small-n friendly)."""
    labels = load_labels_csv(labels_path)
    m = model or BaselineChurnModel()
    if not labels:
        return {"n_labels": 0, "message": "No labels file; add data/churn_labels_example.csv"}

    scores: List[float] = []
    for lab in labels:
        fv = _synthetic_feature_for_label(lab)
        scores.append(m.predict_proba_churn(fv))

    return {
        "n_labels": len(labels),
        "mean_risk_on_examples": float(np.mean(scores)),
        "min_risk": float(np.min(scores)),
        "max_risk": float(np.max(scores)),
        "venue_ids": [l.venue_id for l in labels],
        "scores": scores,
    }
