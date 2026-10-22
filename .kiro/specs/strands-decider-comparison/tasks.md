# Implementation Plan

- [ ] 1. Scaffold the `harness_decider/` package
  - Create `harness_decider/__init__.py` exporting `DeciderHarness` and `TurnResult` once those modules exist (stub exports now, finalize in later tasks).
  - Verify the folder is importable (`python -c "import harness_decider"`).
  - _Requirements: 1.1_

- [ ] 2. Implement the Decider capability registry
  - Create `harness_decider/capabilities.py` with `DECIDER_TOOLS`, a `register` decorator, and `decider_choices()`, mirroring `harness/capabilities.py`.
  - Copy the three capability descriptions (`reset_password`, `unlock_account`, `llm_reasoning`) character-for-character from `harness/capabilities.py`.
  - Write a unit test asserting `DECIDER_TOOLS.keys() == {"reset_password", "unlock_account", "llm_reasoning"}` and that each description string equals `harness.capabilities.TOOLS[name]["description"]` exactly.
  - _Requirements: 1.3, 1.5_

- [ ] 3. Implement `RouteDecision` and the `Decider_Router` protocol
  - Create `harness_decider/decider_router.py` with a `RouteDecision` dataclass (`choice`, `confidence`, `probabilities`) and a `DeciderRouterProtocol` (`route`, `is_injection`, `confirms`).
  - _Requirements: 1.2, 3.1, 3.4, 3.5, 3.6_

- [ ] 4. Implement `FakeDeciderRouter`
  - Add `FakeDeciderRouter` to `harness_decider/decider_router.py` implementing `route`, `is_injection`, `confirms` with deterministic keyword logic, enforcing by construction that `choice` and all `probabilities` keys come from the supplied capability mapping and all numeric outputs are in `[0, 1]`.
  - Write four example-based unit tests comparing `FakeDeciderRouter`'s output band/classification against `FakeJev`'s for the four fixed scripted prompts ("I forgot my password", the SSO/OAuth reasoning prompt, the injection prompt, "help").
  - _Requirements: 3.2, 3.3, 5.1, 5.2, 5.4, 5.5, 5.6_

- [ ] 5. Implement `RealDeciderRouter`
  - Add `RealDeciderRouter` to `harness_decider/decider_router.py` with lazy import of `strands_decider` inside `_ensure_loaded()`, a configurable model id via `DECIDER_MODEL_ID` env var defaulting to `StrandsAgents/strands-decider-2B-hobson-v19`, and `route`/`is_injection`/`confirms` that call `_ensure_loaded()` first and clamp/validate outputs into `[0, 1]` with keys restricted to the supplied capability mapping.
  - Wrap import/load failures in a `RuntimeError` naming the missing dependency or model id.
  - Write a test that imports `harness_decider.decider_router` and constructs `FakeDeciderRouter` with `strands_decider` absent/mocked-absent, asserting no error.
  - Write a test mocking the `strands_decider` import to raise, asserting `RuntimeError` mentions the package/model id and that no decision operation ran.
  - _Requirements: 1.2, 6.1, 6.2, 6.4, 6.5_

- [ ] 6. Implement `make_decider_router()` factory
  - Add the factory to `harness_decider/decider_router.py`, keyed on `DECIDER_MODE` (`offline`/unset → `FakeDeciderRouter`, `live` → `RealDeciderRouter`, unknown → offline default).
  - _Requirements: 5.3, 6.3_

- [ ] 7. Implement `DeciderHarness` orchestration
  - Create `harness_decider/agent.py` with `TurnResult` (same shape as `harness/agent.py`'s) and `DeciderHarness`, reproducing `SupportAgent`'s guardrail → route → confidence-gate → confirmation flow using literal threshold constants (`HI_CONF=0.85`, `LO_CONF=0.50`, `INJECTION_BLOCK=0.80`, confirm `>=0.70`/decline `<=0.30`) and the same `CONFIRM_WORDS`/`DECLINE_WORDS` sets copied as literals (not imported from `harness/agent.py`).
  - Import `make_reasoner` directly from `harness.lc_model` for the `llm_reasoning` capability; do not construct any LangChain/Bedrock chat model class inside `harness_decider/`.
  - In `__init__`, when `DECIDER_MODE=live`, eagerly call `self.decider._ensure_loaded()` so model-load failures surface at construction time.
  - Finalize `harness_decider/__init__.py` exports.
  - Write a static/source-text check that no file under `harness_decider/` imports `ChatBedrockConverse` or another LangChain/Bedrock chat class, and that `harness_decider/agent.py` imports `make_reasoner` from `harness.lc_model`.
  - _Requirements: 1.4, 1.6, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13, 6.4_

- [ ] 8. Add property-based tests for the Decider_Router contract (Properties 1-2)
  - Using `hypothesis`, generate random non-empty capability-name-to-description mappings and arbitrary Unicode user-message strings; assert `FakeDeciderRouter.route()` always returns a valid `RouteDecision` per Property 1, and that `is_injection`/`confirms` always return values in `[0, 1]` per Property 2.
  - Add `hypothesis` to `requirements.txt` as a dev/test dependency if not already present.
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [ ] 9. Add property-based tests for `DeciderHarness` dispatch logic (Properties 3-6)
  - Build a lightweight stub implementing `DeciderRouterProtocol` whose return values are supplied by Hypothesis, and test: guardrail short-circuit on `is_injection >= 0.80` (Property 3), the three-way confidence-band partition (Property 4), confirmation resolution via fast-path words vs. `confirms()` thresholds (Property 5), and reasoning-provider invocation iff capability is `llm_reasoning` (Property 6).
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 4.13_

- [ ] 10. Implement the `compare_demo.py` Comparison_Runner
  - Create `compare_demo.py` at the repo root defining `HarnessResult` and the four fixed scripted prompts (independent list, not imported from `demo.py`'s `SCRIPT`).
  - Construct one `SupportAgent` (from `harness`) and one `DeciderHarness` (from `harness_decider`) once; for each prompt, time and invoke each harness's `.handle()` inside its own `try/except`, recording latency and, on failure, an error result naming the harness and prompt.
  - Print each prompt's paired Jev/Decider results immediately and adjacently before moving to the next prompt.
  - Respect `DEMO_MODE` (Jev side) and `DECIDER_MODE` (Decider side) env vars so default invocation is fully offline.
  - Write an end-to-end offline smoke test asserting all four prompts appear paired in output with no network calls attempted.
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.6, 7.7, 7.8_

- [ ] 11. Add property-based tests for the Comparison_Runner (Properties 7-8)
  - Extract the pairing/printing and failure-isolation logic into testable functions; using Hypothesis-generated synthetic prompt lists (2-10 items) and stub agents that either return canned results or raise on a chosen subset of (harness, prompt) pairs, assert paired results are never interleaved across prompts (Property 7) and that one harness's failure never blocks the other harness or subsequent prompts (Property 8).
  - _Requirements: 7.5, 7.8_

- [ ] 12. Write `harness_decider/COMPARISON.md`
  - Document both approaches: typed-decision provider (hosted TypeSafe API vs. local open-weight model), authentication/access model (API key vs. none/local inference), latency characteristics with citations to each provider's own published figures, and the licensing distinction (hosted proprietary vs. open-source weights).
  - Include runnable commands, prerequisites, and expected output for each `DECIDER_MODE` value (`offline`, `live`) and for running `compare_demo.py`.
  - Write a test parsing the markdown file to assert each required topic/section is present.
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [ ] 13. Verify non-modification of existing files and unchanged `demo.py` behavior
  - Add a test (e.g., via `git diff` against the pre-feature commit, or a stored checksum/snapshot) confirming no file under `harness/` and none of `demo.py`, `README.md`, `scripted_runs.md` changed.
  - Capture a golden snapshot of `python demo.py --script` output under `DEMO_MODE=offline` and assert the current output matches it byte-for-byte.
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

- [ ] 14. Run the full test suite and fix any failures
  - Run all unit, structural, snapshot, and property tests added above; address any failures found.
  - Confirm `python demo.py --script` and `python compare_demo.py` both run cleanly offline with no network access.
  - _Requirements: all_
