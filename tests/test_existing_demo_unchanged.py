"""
Preservation tests: the existing Jev-only demo must behave exactly as before
(Requirements 2.1-2.6).
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXPECTED_SEGMENTS = [
    ("Deterministic (no LLM)", "deterministic_code", "False"),
    ("Reasoning (routes to LangChain)", "langchain_reasoning", "True"),
    ("Guardrail block (Jev Noul)", "guardrail_block", "False"),
    ("Low confidence (escalate)", "escalate_low_confidence", "False"),
]


def test_demo_script_output_matches_documented_behavior():
    env = {"DEMO_MODE": "offline", "PATH": "/usr/bin:/bin"}
    result = subprocess.run(
        [sys.executable, "demo.py", "--script"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=env, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout

    for label, path, used_llm in EXPECTED_SEGMENTS:
        assert f"[{label}]" in output
        assert f"PATH : {path}   (LLM used: {used_llm})" in output

    assert 'STATS: {"turns": 4, "llm_calls": 1, "decided_without_llm": 3}' in output


def test_harness_package_files_untouched():
    harness_dir = REPO_ROOT / "harness"
    expected_files = {"__init__.py", "agent.py", "capabilities.py", "jev_router.py", "lc_model.py"}
    actual_files = {p.name for p in harness_dir.glob("*.py")}
    assert actual_files == expected_files


def test_root_docs_still_describe_jev_only_demo():
    readme = (REPO_ROOT / "README.md").read_text()
    scripted_runs = (REPO_ROOT / "scripted_runs.md").read_text()
    # Spot-check a few literal strings that existed before this feature was added.
    assert "JEV decides" in readme
    assert "Jev `Noul` scores prompt-injection risk" in readme
    assert "turns=4, llm_calls=1, decided_without_llm=3" in scripted_runs
