"""
Lazy-import and failure-message tests for RealDeciderRouter (Requirements 6.2, 6.4).
"""
import builtins
import sys

import pytest

from harness_decider.decider_router import FakeDeciderRouter, RealDeciderRouter


def test_fake_router_works_without_strands_decider_installed(monkeypatch):
    """Constructing/using FakeDeciderRouter must never require strands_decider."""
    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "strands_decider" or name.startswith("strands_decider."):
            raise ImportError("strands_decider must not be imported for offline mode")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    router = FakeDeciderRouter()
    result = router.route("I forgot my password", {"reset_password": "x", "unlock_account": "y", "llm_reasoning": "z"})
    assert result.choice == "reset_password"


def test_real_router_construction_does_not_import_strands_decider(monkeypatch):
    """RealDeciderRouter.__init__ itself must not trigger the import."""
    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "strands_decider" or name.startswith("strands_decider."):
            raise ImportError("strands_decider must not be imported at construction time")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    RealDeciderRouter()  # must not raise


def test_real_router_missing_dependency_raises_descriptive_runtime_error(monkeypatch):
    real_import = builtins.__import__

    def blocking_import(name, *args, **kwargs):
        if name == "strands_decider" or name.startswith("strands_decider."):
            raise ImportError("No module named 'strands_decider'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocking_import)
    router = RealDeciderRouter(model_id="StrandsAgents/strands-decider-2B-hobson-v19")
    with pytest.raises(RuntimeError) as exc_info:
        router.route("hello", {"a": "x"})
    message = str(exc_info.value)
    assert "strands-decider" in message
    assert "StrandsAgents/strands-decider-2B-hobson-v19" in message
