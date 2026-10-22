"""
Property-based tests for DeciderHarness's dispatch logic (Properties 3-6,
Requirements 4.1-4.13), using a stub Decider_Router whose return values are
supplied by Hypothesis. This decouples the harness-logic properties from any
specific router implementation.

Feature: strands-decider-comparison, Property 3: Injection guardrail short-circuits the turn
Feature: strands-decider-comparison, Property 4: Confidence partitions into exactly one of three bands
Feature: strands-decider-comparison, Property 5: Confirmation resolution is a pure function of reply and confirm-probability
Feature: strands-decider-comparison, Property 6: Reasoning provider invoked if and only if the capability is llm_reasoning
"""
from hypothesis import given, settings, strategies as st

from harness_decider.decider_router import RouteDecision
from harness_decider import agent as agent_module
from harness_decider.agent import DeciderHarness


class StubRouter:
    """Fully controllable stand-in for the Decider_Router protocol."""

    def __init__(self, injection_p=0.0, route_result=None, confirms_p=0.5):
        self._injection_p = injection_p
        self._route_result = route_result or RouteDecision(
            choice="reset_password", confidence=0.9,
            probabilities={"reset_password": 0.9, "unlock_account": 0.05, "llm_reasoning": 0.05},
        )
        self._confirms_p = confirms_p
        self.route_called = False
        self.confirms_called = False

    def route(self, user_message, capabilities):
        self.route_called = True
        return self._route_result

    def is_injection(self, text):
        return self._injection_p

    def confirms(self, text, pending_action):
        self.confirms_called = True
        return self._confirms_p


class StubReasoner:
    def __init__(self):
        self.calls = 0

    def reason(self, user_message, system_prompt):
        self.calls += 1
        return "stub answer"


def make_harness(router: StubRouter, reasoner: StubReasoner) -> DeciderHarness:
    harness = DeciderHarness.__new__(DeciderHarness)  # bypass __init__'s factory calls
    harness.decider = router
    harness.reasoner = reasoner
    harness.llm_calls = 0
    harness.turns = 0
    harness.pending_confirmation = None
    return harness


@settings(max_examples=100)
@given(injection_p=st.floats(min_value=0.80, max_value=1.0))
def test_property_3_guardrail_short_circuits(injection_p):
    router = StubRouter(injection_p=injection_p)
    reasoner = StubReasoner()
    harness = make_harness(router, reasoner)
    result = harness.handle("any message")
    assert result.path == "guardrail_block"
    assert router.route_called is False
    assert reasoner.calls == 0


@settings(max_examples=100)
@given(confidence=st.floats(min_value=0.0, max_value=1.0))
def test_property_4_confidence_band_partition(confidence):
    route_result = RouteDecision(
        choice="reset_password", confidence=confidence,
        probabilities={"reset_password": confidence, "unlock_account": 0.0, "llm_reasoning": 0.0},
    )
    router = StubRouter(injection_p=0.0, route_result=route_result)
    reasoner = StubReasoner()
    harness = make_harness(router, reasoner)
    result = harness.handle("some request")

    if confidence >= 0.85:
        assert result.path == "deterministic_code"
    elif confidence >= 0.50:
        assert result.path == "clarify_medium_confidence"
        assert harness.pending_confirmation is not None
    else:
        assert result.path == "escalate_low_confidence"
        assert harness.pending_confirmation is None


@settings(max_examples=100)
@given(confirm_p=st.floats(min_value=0.0, max_value=1.0))
def test_property_5_confirmation_resolution_via_probability(confirm_p):
    router = StubRouter(injection_p=0.0, confirms_p=confirm_p)
    reasoner = StubReasoner()
    harness = make_harness(router, reasoner)
    harness.pending_confirmation = ("reset_password", "I forgot my password")

    result = harness.handle("maybe i guess")  # not a fast-path word

    if confirm_p >= 0.70:
        assert result.path == "deterministic_code"
        assert harness.pending_confirmation is None
    elif confirm_p <= 0.30:
        assert result.path == "confirmation_declined"
        assert harness.pending_confirmation is None
    else:
        assert result.path == "confirmation_ambiguous"
        assert harness.pending_confirmation is not None


@given(word=st.sampled_from(sorted(agent_module.CONFIRM_WORDS | agent_module.DECLINE_WORDS)))
def test_property_5_fast_path_words_never_call_confirms(word):
    router = StubRouter(injection_p=0.0)
    reasoner = StubReasoner()
    harness = make_harness(router, reasoner)
    harness.pending_confirmation = ("reset_password", "I forgot my password")

    harness.handle(word)
    assert router.confirms_called is False


@settings(max_examples=100)
@given(capability=st.sampled_from(["reset_password", "unlock_account", "llm_reasoning"]))
def test_property_6_reasoner_invoked_iff_llm_reasoning(capability):
    route_result = RouteDecision(
        choice=capability, confidence=0.99,
        probabilities={"reset_password": 0.0, "unlock_account": 0.0, "llm_reasoning": 0.0},
    )
    router = StubRouter(injection_p=0.0, route_result=route_result)
    reasoner = StubReasoner()
    harness = make_harness(router, reasoner)

    harness.handle("a message")

    if capability == "llm_reasoning":
        assert reasoner.calls == 1
    else:
        assert reasoner.calls == 0
