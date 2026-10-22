"""
Structural checks on harness_decider/COMPARISON.md (Requirements 8.1-8.7).
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC = REPO_ROOT / "harness_decider" / "COMPARISON.md"


def test_comparison_doc_exists():
    assert DOC.exists()


def test_comparison_doc_covers_required_topics():
    text = DOC.read_text().lower()
    assert "typesafe" in text and "strands decider" in text  # provider identification
    assert "api key" in text  # auth model
    assert "latency" in text and "strandsagents.com" in text  # latency w/ citation
    assert "open source" in text or "open-source" in text  # licensing
    assert "decider_mode" in text  # decision mode run instructions
    assert "compare_demo.py" in text  # comparison runner run instructions
