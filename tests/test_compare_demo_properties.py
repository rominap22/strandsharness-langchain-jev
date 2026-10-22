"""
Property-based tests for compare_demo.py's pairing/isolation mechanism
(Properties 7-8, Requirements 7.5, 7.8), using synthetic stub agents so the
general print-pairing and failure-isolation mechanism is exercised directly,
not just the fixed four scripted prompts.

Feature: strands-decider-comparison, Property 7: Paired-result printing is never interleaved across prompts
Feature: strands-decider-comparison, Property 8: Per-harness, per-prompt failure isolation
"""
from hypothesis import given, settings, strategies as st

from compare_demo import run_comparison


class FakeTurnResult:
    def __init__(self, path="deterministic_code"):
        self.path = path
        self.used_llm = False
        self.detail = {}
        self.text = "stub reply"


class StubAgent:
    """Raises on invocations whose index is in `fail_indices`; else succeeds."""

    def __init__(self, fail_indices: set[int]):
        self._fail_indices = fail_indices
        self._call_count = 0

    def handle(self, msg):
        idx = self._call_count
        self._call_count += 1
        if idx in self._fail_indices:
            raise RuntimeError(f"synthetic failure at call {idx}")
        return FakeTurnResult()


prompt_lists = st.lists(
    st.tuples(st.text(min_size=1, max_size=10), st.text(min_size=1, max_size=10)),
    min_size=2, max_size=10,
)


@settings(max_examples=100)
@given(prompts=prompt_lists)
def test_property_7_paired_results_never_interleaved(prompts):
    jev_agent = StubAgent(fail_indices=set())
    decider_agent = StubAgent(fail_indices=set())

    emitted_order: list[str] = []

    def emit_pair(label, msg, jev_result, decider_result):
        emitted_order.append(f"jev:{label}")
        emitted_order.append(f"decider:{label}")

    run_comparison(prompts, jev_agent, decider_agent, emit_pair)

    # For every prompt, its jev/decider entries must be adjacent in emission order.
    for label, _ in prompts:
        jev_idx = emitted_order.index(f"jev:{label}")
        decider_idx = emitted_order.index(f"decider:{label}")
        assert decider_idx == jev_idx + 1


@settings(max_examples=100)
@given(
    prompts=prompt_lists,
    failing_prompt_index=st.integers(min_value=0, max_value=9),
    fail_jev=st.booleans(),
    fail_decider=st.booleans(),
)
def test_property_8_failure_isolation(prompts, failing_prompt_index, fail_jev, fail_decider):
    n = len(prompts)
    failing_prompt_index = failing_prompt_index % n

    jev_fail_indices = {failing_prompt_index} if fail_jev else set()
    decider_fail_indices = {failing_prompt_index} if fail_decider else set()

    jev_agent = StubAgent(fail_indices=jev_fail_indices)
    decider_agent = StubAgent(fail_indices=decider_fail_indices)

    pairs = run_comparison(prompts, jev_agent, decider_agent, emit_pair=lambda *a: None)

    assert len(pairs) == n  # every prompt was processed, none skipped

    for i, (jev_result, decider_result) in enumerate(pairs):
        if i == failing_prompt_index and fail_jev:
            assert jev_result.error is not None
        else:
            assert jev_result.error is None

        if i == failing_prompt_index and fail_decider:
            assert decider_result.error is not None
        else:
            assert decider_result.error is None
