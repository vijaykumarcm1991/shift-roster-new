"""Tests for the core.config Settings validators."""

import importlib

import pytest

import app.core.config as cfg


@pytest.fixture
def reload_config():
    """Reload the config module to pick up env var changes per test."""
    importlib.reload(cfg)
    yield
    importlib.reload(cfg)


def test_default_secret_accepted_in_development(reload_config, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "change-me")
    s = cfg.Settings()
    assert s.secret_key == "change-me"


def test_custom_secret_accepted_in_development(reload_config, monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("SECRET_KEY", "my-strong-secret")
    s = cfg.Settings()
    assert s.secret_key == "my-strong-secret"


def test_default_secret_rejected_in_production(reload_config, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "change-me")
    with pytest.raises(Exception) as exc_info:
        cfg.Settings()
    assert "SECRET_KEY" in str(exc_info.value)


def test_custom_secret_accepted_in_production(reload_config, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "my-strong-secret")
    s = cfg.Settings()
    assert s.secret_key == "my-strong-secret"
