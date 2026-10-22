"""
Property-based tests for the Decider_Router contract (Properties 1-2,
Requirements 3.1-3.5), run against FakeDeciderRouter since it is the only
router safe to exercise 100+ times with no cost/network.

Feature: strands-decider-comparison, Property 1: Routing_Result validity and domain closure
Feature: strands-decider-comparison, Property 2: Noul-style probabilities are always bounded
"""
from hypothesis import given, settings, strategies as st

from harness_decider.decider_router import FakeDeciderRouter

capability_names = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd"), max_codepoint=0x7A),
    min_size=1, max_size=20,
).filter(lambda s: s.strip() != "")

capability_maps = st.dictionaries(
    keys=capability_names,
    values=st.text(min_size=0, max_size=50),
    min_size=1, max_size=8,
)

user_messages = st.text(min_size=0, max_size=200)


@settings(max_examples=100)
@given(capabilities=capability_maps, message=user_messages)
def test_property_1_routing_result_validity(capabilities, message):
    router = FakeDeciderRouter()
    result = router.route(message, capabilities)
    assert result.choice in capabilities
    assert 0.0 <= result.confidence <= 1.0
    for name, prob in result.probabilities.items():
        assert name in capabilities
        assert 0.0 <= prob <= 1.0


@settings(max_examples=100)
@given(text=user_messages)
def test_property_2_is_injection_bounded(text):
    router = FakeDeciderRouter()
    value = router.is_injection(text)
    assert 0.0 <= value <= 1.0


@settings(max_examples=100)
@given(text=user_messages, pending=capability_names)
def test_property_2_confirms_bounded(text, pending):
    router = FakeDeciderRouter()
    value = router.confirms(text, pending)
    assert 0.0 <= value <= 1.0
