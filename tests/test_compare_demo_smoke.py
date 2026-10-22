"""
End-to-end offline smoke test for compare_demo.py (Requirements 7.1, 7.2, 7.3,
7.4, 7.6).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_compare_demo_runs_offline_and_pairs_all_four_prompts():
    env = {"DEMO_MODE": "offline", "DECIDER_MODE": "offline", "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "compare_demo.py"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=env, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout

    expected_labels = [
        "Deterministic (no LLM)",
        "Reasoning (routes to LangChain)",
        "Guardrail block",
        "Low confidence (escalate)",
    ]
    for label in expected_labels:
        assert f"[{label}]" in output

    assert output.count("JEV      :") == 4
    assert output.count("DECIDER  :") == 4
    assert "STATS jev" in output
    assert "STATS decider" in output
