"""
Tests for app/config.py — environment variable parsing and defaults.
"""

import os
from unittest.mock import patch


class TestAllowedOrigins:

    def test_default_is_wildcard(self):
        with patch.dict(os.environ, {}, clear=False):
            # Remove ALLOWED_ORIGINS if set, to test the default
            env = {k: v for k, v in os.environ.items() if k != "ALLOWED_ORIGINS"}
            with patch.dict(os.environ, env, clear=True):
                # Re-import to pick up the new env
                import importlib
                import app.config as cfg
                importlib.reload(cfg)
                assert cfg.ALLOWED_ORIGINS == ["*"]

    def test_single_origin(self):
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://example.com"}, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.ALLOWED_ORIGINS == ["https://example.com"]

    def test_multiple_origins(self):
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://a.com, https://b.com"}, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.ALLOWED_ORIGINS == ["https://a.com", "https://b.com"]

    def test_wildcard_explicit(self):
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "*"}, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.ALLOWED_ORIGINS == ["*"]


class TestConfigDefaults:

    def test_sim_tick_interval_default(self):
        env = {k: v for k, v in os.environ.items() if k != "SIM_TICK_INTERVAL"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.SIM_TICK_INTERVAL == 2.0

    def test_sim_speed_default(self):
        env = {k: v for k, v in os.environ.items() if k != "SIM_SPEED"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.SIM_SPEED == 10.0

    def test_seed_warehouses_default(self):
        env = {k: v for k, v in os.environ.items() if k != "SEED_WAREHOUSES"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.SEED_WAREHOUSES == 10

    def test_risk_threshold_default(self):
        env = {k: v for k, v in os.environ.items() if k != "RISK_THRESHOLD"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.RISK_THRESHOLD == 0.6

    def test_risk_model_retrain_interval_default(self):
        env = {
            k: v
            for k, v in os.environ.items()
            if k != "RISK_MODEL_RETRAIN_INTERVAL_CYCLES"
        }
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.RISK_MODEL_RETRAIN_INTERVAL_CYCLES == 10

    def test_llm_call_cooldown_default(self):
        env = {k: v for k, v in os.environ.items() if k != "LLM_CALL_COOLDOWN"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.LLM_CALL_COOLDOWN == 300.0

    def test_smtp_use_tls_default_true(self):
        env = {k: v for k, v in os.environ.items() if k != "SMTP_USE_TLS"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.SMTP_USE_TLS is True

    def test_smtp_use_tls_false(self):
        with patch.dict(os.environ, {"SMTP_USE_TLS": "false"}, clear=False):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.SMTP_USE_TLS is False

    def test_lifecycle_target_active_default(self):
        env = {k: v for k, v in os.environ.items() if k != "LIFECYCLE_TARGET_ACTIVE"}
        with patch.dict(os.environ, env, clear=True):
            import importlib
            import app.config as cfg
            importlib.reload(cfg)
            assert cfg.LIFECYCLE_TARGET_ACTIVE == 60
