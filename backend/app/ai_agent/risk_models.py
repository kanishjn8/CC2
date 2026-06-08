"""
Risk detection models — ML-based delay prediction plus rule-based
bottleneck and carrier degradation detection.
"""

import logging
import threading
from datetime import datetime
from typing import Sequence

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler

from app.config import BOTTLENECK_THRESHOLD, CARRIER_RELIABILITY_THRESHOLD

log = logging.getLogger("cc2.risk_models")

FEATURE_NAMES = [
    "distance",
    "traffic_level",
    "weather_factor",
    "congestion_score",
    "reliability_score",
    "delay_probability",
    "pickup_success_rate",
    "eta_sla_buffer_hours",
]


class DelayRiskModel:
    """Gradient Boosting model with synthetic warm-start and real-data retraining."""

    def __init__(self):
        self.model: GradientBoostingClassifier | None = None
        self.scaler: StandardScaler | None = None
        self._trained = False
        self._lock = threading.RLock()
        self._training_metadata: dict = {
            "source": "untrained",
            "synthetic_samples": 0,
            "real_samples": 0,
            "accuracy": None,
            "trained_at": None,
        }

    @property
    def is_trained(self) -> bool:
        with self._lock:
            return self._trained

    def train(
        self,
        n_samples: int = 5000,
        training_samples: Sequence[tuple[dict, int]] | None = None,
        real_sample_weight: float = 4.0,
    ) -> dict:
        """Train on synthetic data, optionally weighted with resolved real outcomes."""
        X, y = self._generate_synthetic_data(n_samples)
        sample_weight = np.ones(len(y), dtype=float)
        real_count = 0

        if training_samples:
            X_real, y_real = self._samples_to_arrays(training_samples)
            if len(y_real) > 0:
                X = np.vstack([X, X_real])
                y = np.concatenate([y, y_real])
                real_count = len(y_real)
                sample_weight = np.concatenate([
                    sample_weight,
                    np.full(real_count, real_sample_weight, dtype=float),
                ])

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_scaled, y, sample_weight=sample_weight)
        accuracy = model.score(X_scaled, y)

        metadata = {
            "source": "hybrid" if real_count else "synthetic",
            "synthetic_samples": int(n_samples),
            "real_samples": int(real_count),
            "accuracy": round(float(accuracy), 4),
            "trained_at": datetime.utcnow().isoformat(),
        }
        with self._lock:
            self.scaler = scaler
            self.model = model
            self._trained = True
            self._training_metadata = metadata

        log.info(
            "Delay risk model trained — source=%s synthetic=%d real=%d accuracy=%.3f",
            metadata["source"], n_samples, real_count, accuracy,
        )
        return metadata

    def predict(self, features: dict) -> float:
        """Return delay probability (0–1) for a single shipment."""
        with self._lock:
            model = self.model
            scaler = self.scaler
            trained = self._trained

        if not trained or model is None or scaler is None:
            return self._heuristic_predict(features)

        X = np.array([[features[f] for f in FEATURE_NAMES]])
        X_scaled = scaler.transform(X)
        proba = model.predict_proba(X_scaled)[0]
        return float(proba[1]) if len(proba) > 1 else float(proba[0])

    def get_feature_importance(self) -> dict[str, float]:
        """Return feature importances from the trained model."""
        with self._lock:
            model = self.model
            trained = self._trained

        if not trained or model is None:
            return {}
        importances = model.feature_importances_
        return dict(zip(FEATURE_NAMES, [round(float(v), 4) for v in importances]))

    def get_training_summary(self) -> dict:
        """Return metadata about the currently loaded training run."""
        with self._lock:
            return dict(self._training_metadata)

    def _heuristic_predict(self, features: dict) -> float:
        """Fallback weighted heuristic when model is not yet trained."""
        score = (
            0.15 * (features["distance"] / 2500)
            + 0.20 * (features["traffic_level"] / 3)
            + 0.10 * ((features["weather_factor"] - 0.5) / 1.5)
            + 0.15 * features["congestion_score"]
            + 0.20 * (1 - features["reliability_score"])
            + 0.10 * features["delay_probability"]
            + 0.05 * (1 - features["pickup_success_rate"])
            + 0.15 * max(0.0, min(1.0, 1 - features["eta_sla_buffer_hours"] / 24))
        )
        return float(np.clip(score, 0.0, 1.0))

    @staticmethod
    def _samples_to_arrays(samples: Sequence[tuple[dict, int]]):
        """Convert validated feature dictionaries and labels to sklearn arrays."""
        rows = []
        labels = []
        for features, label in samples:
            rows.append([float(features[name]) for name in FEATURE_NAMES])
            labels.append(int(label))
        return np.array(rows, dtype=float), np.array(labels, dtype=int)

    @staticmethod
    def _generate_synthetic_data(n: int):
        """Generate synthetic training data mimicking real logistics patterns."""
        rng = np.random.RandomState(42)

        distance = rng.uniform(100, 2500, n)
        traffic = rng.choice([0, 1, 2, 3], n, p=[0.30, 0.35, 0.25, 0.10])
        weather = rng.uniform(0.5, 2.0, n)
        congestion = rng.uniform(0.0, 1.0, n)
        reliability = rng.uniform(0.3, 1.0, n)
        delay_prob = rng.uniform(0.0, 0.8, n)
        pickup_rate = rng.uniform(0.4, 1.0, n)
        buffer_hours = rng.uniform(-5, 30, n)

        X = np.column_stack([
            distance, traffic, weather, congestion,
            reliability, delay_prob, pickup_rate, buffer_hours,
        ])

        # Weighted risk score — simulates real delay patterns
        risk = (
            0.15 * (distance / 2500)
            + 0.20 * (traffic / 3)
            + 0.10 * ((weather - 0.5) / 1.5)
            + 0.15 * congestion
            + 0.20 * (1 - reliability)
            + 0.10 * delay_prob
            + 0.05 * (1 - pickup_rate)
            + 0.15 * np.clip(1 - buffer_hours / 24, 0, 1)
        )
        noise = rng.normal(0, 0.08, n)
        risk = np.clip(risk + noise, 0, 1)
        y = (risk > 0.45).astype(int)

        return X, y


# ── Rule-based detectors ─────────────────────────────────────────────────────


def detect_bottlenecks(warehouses: list, threshold: float = BOTTLENECK_THRESHOLD) -> list[dict]:
    """Detect warehouses whose congestion exceeds the threshold."""
    bottlenecks = []
    for wh in warehouses:
        if wh.congestion_score > threshold:
            bottlenecks.append({
                "warehouse_id": wh.warehouse_id,
                "location": wh.location,
                "congestion_score": wh.congestion_score,
                "current_load": wh.current_load,
                "capacity": wh.capacity,
                "queue_length": wh.queue_length,
            })
    return bottlenecks


def detect_carrier_degradation(
    carriers: list, threshold: float = CARRIER_RELIABILITY_THRESHOLD
) -> list[dict]:
    """Detect carriers whose reliability has dropped below acceptable levels."""
    degraded = []
    for c in carriers:
        if c.reliability_score < threshold:
            degraded.append({
                "carrier_id": c.carrier_id,
                "name": c.name,
                "reliability_score": c.reliability_score,
                "delay_probability": c.delay_probability,
                "pickup_success_rate": c.pickup_success_rate,
                "total_delays": c.total_delays,
                "total_shipments": c.total_shipments,
            })
    return degraded
