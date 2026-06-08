"""
Tests for the AI agent risk models — ML model training, prediction,
heuristic fallback, and feature importance.
"""

import pytest

from app.ai_agent.risk_models import DelayRiskModel, FEATURE_NAMES


@pytest.fixture(scope="module")
def trained_model():
    """Train once for the module to save time."""
    model = DelayRiskModel()
    model.train(n_samples=500)
    return model


def _sample_features(**overrides):
    """Return a dict of sample feature values."""
    defaults = {
        "distance": 1200.0,
        "traffic_level": 2,
        "weather_factor": 1.2,
        "congestion_score": 0.5,
        "reliability_score": 0.85,
        "delay_probability": 0.15,
        "pickup_success_rate": 0.92,
        "eta_sla_buffer_hours": 10.0,
    }
    defaults.update(overrides)
    return defaults


class TestDelayRiskModelInit:

    def test_not_trained_initially(self):
        m = DelayRiskModel()
        assert m.is_trained is False

    def test_model_is_none_initially(self):
        m = DelayRiskModel()
        assert m.model is None
        assert m.scaler is None


class TestTraining:

    def test_train_sets_trained_flag(self, trained_model):
        assert trained_model.is_trained is True

    def test_train_creates_model(self, trained_model):
        assert trained_model.model is not None
        assert trained_model.scaler is not None

    def test_train_small_sample(self):
        m = DelayRiskModel()
        m.train(n_samples=50)
        assert m.is_trained is True

    def test_training_summary_tracks_synthetic_source(self):
        m = DelayRiskModel()
        summary = m.train(n_samples=50)

        assert summary["source"] == "synthetic"
        assert summary["synthetic_samples"] == 50
        assert summary["real_samples"] == 0
        assert m.get_training_summary()["source"] == "synthetic"

    def test_train_with_real_samples_marks_hybrid_source(self):
        m = DelayRiskModel()
        samples = [
            (_sample_features(distance=300, eta_sla_buffer_hours=24), 0),
            (_sample_features(distance=2300, eta_sla_buffer_hours=-3), 1),
        ]
        summary = m.train(n_samples=50, training_samples=samples)

        assert summary["source"] == "hybrid"
        assert summary["real_samples"] == 2
        assert m.is_trained is True


class TestPredict:

    def test_returns_float(self, trained_model):
        features = _sample_features()
        result = trained_model.predict(features)
        assert isinstance(result, float)

    def test_returns_between_0_and_1(self, trained_model):
        features = _sample_features()
        result = trained_model.predict(features)
        assert 0.0 <= result <= 1.0

    def test_high_risk_scenario(self, trained_model):
        """Very bad conditions should produce high risk."""
        features = _sample_features(
            distance=2500,
            traffic_level=3,
            weather_factor=2.0,
            congestion_score=0.95,
            reliability_score=0.3,
            delay_probability=0.8,
            pickup_success_rate=0.4,
            eta_sla_buffer_hours=-2.0,
        )
        result = trained_model.predict(features)
        assert result > 0.3  # should be elevated

    def test_low_risk_scenario(self, trained_model):
        """Good conditions should produce lower risk."""
        features = _sample_features(
            distance=200,
            traffic_level=0,
            weather_factor=0.8,
            congestion_score=0.1,
            reliability_score=0.98,
            delay_probability=0.02,
            pickup_success_rate=0.99,
            eta_sla_buffer_hours=24.0,
        )
        result = trained_model.predict(features)
        assert result < 0.7  # should be lower


class TestHeuristicPredict:

    def test_untrained_model_uses_heuristic(self):
        m = DelayRiskModel()
        features = _sample_features()
        result = m.predict(features)
        assert 0.0 <= result <= 1.0

    def test_heuristic_high_risk(self):
        m = DelayRiskModel()
        features = _sample_features(
            distance=2500,
            traffic_level=3,
            weather_factor=2.0,
            congestion_score=1.0,
            reliability_score=0.3,
            delay_probability=0.8,
            pickup_success_rate=0.4,
            eta_sla_buffer_hours=-5.0,
        )
        result = m.predict(features)
        assert result > 0.4

    def test_heuristic_low_risk(self):
        m = DelayRiskModel()
        features = _sample_features(
            distance=100,
            traffic_level=0,
            weather_factor=0.5,
            congestion_score=0.0,
            reliability_score=1.0,
            delay_probability=0.0,
            pickup_success_rate=1.0,
            eta_sla_buffer_hours=30.0,
        )
        result = m.predict(features)
        assert result < 0.3


class TestFeatureImportance:

    def test_returns_dict(self, trained_model):
        fi = trained_model.get_feature_importance()
        assert isinstance(fi, dict)

    def test_all_features_present(self, trained_model):
        fi = trained_model.get_feature_importance()
        for f in FEATURE_NAMES:
            assert f in fi

    def test_values_are_floats(self, trained_model):
        fi = trained_model.get_feature_importance()
        for v in fi.values():
            assert isinstance(v, float)

    def test_untrained_returns_empty(self):
        m = DelayRiskModel()
        assert m.get_feature_importance() == {}


class TestSyntheticData:

    def test_shape(self):
        X, y = DelayRiskModel._generate_synthetic_data(100)
        assert X.shape == (100, len(FEATURE_NAMES))
        assert y.shape == (100,)

    def test_labels_are_binary(self):
        _, y = DelayRiskModel._generate_synthetic_data(100)
        assert set(y).issubset({0, 1})

    def test_deterministic(self):
        """Same seed → same data."""
        X1, y1 = DelayRiskModel._generate_synthetic_data(50)
        X2, y2 = DelayRiskModel._generate_synthetic_data(50)
        assert (X1 == X2).all()
        assert (y1 == y2).all()
