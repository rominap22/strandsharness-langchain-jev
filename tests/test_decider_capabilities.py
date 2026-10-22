"""
Structural tests for harness_decider/capabilities.py (Requirements 1.3, 1.5).
"""
from harness.capabilities import TOOLS
from harness_decider.capabilities import DECIDER_TOOLS


def test_decider_capability_names_match_jev_exactly():
    assert set(DECIDER_TOOLS.keys()) == {"reset_password", "unlock_account", "llm_reasoning"}
    assert set(DECIDER_TOOLS.keys()) == set(TOOLS.keys())


def test_decider_capability_descriptions_match_jev_character_for_character():
    for name in TOOLS:
        assert DECIDER_TOOLS[name]["description"] == TOOLS[name]["description"], (
            f"Description for '{name}' differs between harness/capabilities.py "
            "and harness_decider/capabilities.py"
        )
