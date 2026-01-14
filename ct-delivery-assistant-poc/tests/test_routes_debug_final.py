import os

from app.routes import debug as dbg


def test_enabled_variants(monkeypatch):
    for v in ["1", "true", "yes", "y", "on"]:
        monkeypatch.setenv("ENABLE_DEBUG_ROUTES", v)
        assert dbg._enabled() is True

    for v in ["0", "false", "no", "n", "off", ""]:
        monkeypatch.setenv("ENABLE_DEBUG_ROUTES", v)
        assert dbg._enabled() is False


def test_require_enabled_raises(monkeypatch):
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "0")
    # should raise
    try:
        dbg._require_enabled()
        assert False, "expected HTTPException"
    except Exception as e:
        from fastapi import HTTPException

        assert isinstance(e, HTTPException)
