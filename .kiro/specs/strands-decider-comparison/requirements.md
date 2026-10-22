# Requirements Document

## Introduction

This feature adds a second, parallel implementation of the existing IT-support harness demo that uses **Strands Decider** (`strands-decider-2b`) as the typed-decision layer instead of **Jev** (TypeSafe System One). The goal is to let both decision providers be run and compared side by side against identical prompts, for the identical set of capabilities (`reset_password`, `unlock_account`, `llm_reasoning`), while leaving the existing Jev-based harness in `harness/` completely unchanged.

The new implementation lives in its own folder, mirrors the structure of the existing harness (decision router, capability registry, agent orchestration, LangChain reasoning), and supports both an offline/stubbed mode (no model weights or network required) and a real mode that loads and calls the actual `strands-decider` model. A comparison demo script runs the same scripted inputs through both harnesses and reports routing decision, confidence, path taken, and latency for each. Documentation explains the two approaches and how to run each.

## Glossary

- **Decider_Harness**: The new orchestration component, analogous to `SupportAgent` in `harness/agent.py`, that uses Strands Decider as its typed-decision layer.
- **Decider_Router**: The component, analogous to `JevRouter`/`FakeJev` in `harness/jev_router.py`, responsible for issuing Choice and Noul questions to Strands Decider and returning typed routing/guardrail/confirmation results.
- **Real_Decider_Router**: The Decider_Router implementation that loads and invokes the actual `strands-decider` model (local CPU/GPU inference, no API key).
- **Fake_Decider_Router**: The Decider_Router implementation that returns deterministic, keyword-based typed results with no model weights or network access, mirroring `FakeJev`.
- **Decider_Capability_Registry**: The capability registry used by the Decider_Harness, exposing `reset_password`, `unlock_account`, and `llm_reasoning` with the same descriptions as the existing `harness/capabilities.py` registry.
- **Reasoning_Provider**: The LangChain/Bedrock-backed component that generates free-text answers for the `llm_reasoning` capability, reused or mirrored from `harness/lc_model.py`.
- **Comparison_Runner**: The script or extended demo that executes the same set of scripted prompts against both the Jev-based harness and the Decider_Harness and reports results for each.
- **Decision_Mode**: An environment-configurable setting (analogous to `DEMO_MODE`) that selects between offline/stubbed and real behavior for the Decider_Router.
- **Routing_Result**: The structured output of a routing decision, containing the selected capability, a confidence score, and a probability distribution over capabilities.
- **Confidence_Gate**: The threshold logic that maps a Routing_Result's confidence to one of three branches: act (`>= 0.85`), clarify (`0.50`–`0.85`), or escalate (`< 0.50`).

## Requirements

### Requirement 1: Decider Harness Package Structure

**User Story:** As a developer comparing decision-layer providers, I want a new, self-contained package that mirrors the existing Jev harness's structure, so that I can understand and maintain the Strands Decider implementation using the same mental model as the existing code.

#### Acceptance Criteria

1. THE Decider_Harness SHALL reside in a new top-level folder distinct from `harness/` (for example `harness_decider/`), WHERE the folder name SHALL NOT equal `harness`, and the folder SHALL contain an `__init__.py` file making it a valid, importable Python package.
2. THE Decider_Harness folder SHALL contain a router module that defines the `Decider_Router` interface along with its `Fake_Decider_Router` and `Real_Decider_Router` implementations, analogous in role to `JevRouter` and `FakeJev` in `harness/jev_router.py`.
3. THE Decider_Harness folder SHALL contain a capability registry module that defines the `Decider_Capability_Registry`, analogous in role to the `TOOLS` registry in `harness/capabilities.py`.
4. THE Decider_Harness folder SHALL contain an agent orchestration module that defines the `Decider_Harness` orchestration class, analogous in role to `SupportAgent` in `harness/agent.py`.
5. THE Decider_Capability_Registry SHALL expose a capability name set that is exactly equal to `{"reset_password", "unlock_account", "llm_reasoning"}`, and for each of these names SHALL expose a capability description string that is exactly equal, character for character, to the corresponding description string in the existing `harness/capabilities.py` `TOOLS` registry.
6. THE Decider_Harness orchestration class SHALL, for the `llm_reasoning` capability, import and invoke the `make_reasoner` factory from `harness/lc_model.py` to obtain its reasoning provider, and SHALL NOT independently construct, import, or instantiate any LangChain or Bedrock chat model class (for example `ChatBedrockConverse`) within the Decider_Harness folder.

### Requirement 2: Preservation of Existing Jev Harness

**User Story:** As a maintainer of the existing booth demo, I want the Strands Decider work to be strictly additive, so that the current Jev-based demo continues to work exactly as before.

#### Acceptance Criteria

1. THE Decider_Harness implementation SHALL NOT add, delete, or modify any file under the existing `harness/` folder (`__init__.py`, `agent.py`, `capabilities.py`, `jev_router.py`, `lc_model.py`).
2. THE Decider_Harness implementation SHALL NOT modify `demo.py`'s behavior, in interactive mode or `--script` mode, when `demo.py` is invoked with no command-line arguments beyond the existing `--script` flag and no environment variables beyond the existing `DEMO_MODE` values (`offline`, `adapter`, `live`).
3. THE Decider_Harness implementation SHALL NOT modify the existing content of `README.md` or `scripted_runs.md` that describes the Jev-only demo; new content about the Decider work SHALL only be appended as new sections.
4. WHEN `demo.py --script` is run with `DEMO_MODE=offline` after the Decider_Harness implementation is added, THE System SHALL print, for each of the 4 scripted segments in unchanged order, a block starting with the segment label line (`[<label>]`), followed by a `USER: <message>` line, a `JEV  :` line containing the JSON-serialized decision detail, a `PATH : <path>   (LLM used: <bool>)` line, and an `AGENT: <response text>` line, with `<path>` and `<bool>` for each segment identical to the current behavior's values (`deterministic_code`/`False` for segment 1, `langchain_reasoning`/`True` for segment 2, `guardrail_block`/`False` for segment 3, `escalate_low_confidence`/`False` for segment 4).
5. WHEN `demo.py --script` completes all 4 scripted segments with `DEMO_MODE=offline`, THE System SHALL print a final line in the form `STATS: {"turns": 4, "llm_calls": 1, "decided_without_llm": 3}` before exiting.
6. IF the Decider_Harness implementation is present but `DEMO_MODE` is unset or set to `offline`, THEN THE System SHALL route all 4 scripted segments using `FakeJev` exclusively, performing zero calls to `typesafe_sdk`, `system_one_adapter`, or any Bedrock/LangChain model.

### Requirement 3: Typed Routing Decisions via Strands Decider

**User Story:** As a developer, I want the Decider_Router to answer the same kinds of typed questions Jev answers, so that the Decider_Harness can reuse the same confidence-gate and guardrail logic as the Jev harness.

#### Acceptance Criteria

1. THE Decider_Router SHALL provide a `route` operation that accepts a user message and a mapping of capability name to capability description and returns a Routing_Result containing a selected capability, a confidence score, and a probability distribution over capabilities.
2. THE selected capability and every key in the Routing_Result's probability distribution returned by the `route` operation SHALL be one of the capability names supplied in that operation's capability mapping.
3. THE confidence score and every probability value returned by the `route` operation SHALL be in the range `[0, 1]`.
4. THE Decider_Router SHALL provide an `is_injection` operation that accepts user text and returns a probability, in the range `[0, 1]`, that the text is a prompt-injection or policy-violation attempt.
5. THE Decider_Router SHALL provide a `confirms` operation that accepts a user reply and a pending capability name and returns a probability, in the range `[0, 1]`, that the reply confirms proceeding with the pending capability.
6. THE Routing_Result returned by the Decider_Router SHALL use the same field names (`choice`, `confidence`, `probabilities`) as the `RouteDecision` structure used by the existing Jev router.

### Requirement 4: Decider Harness Orchestration and Confidence Gate

**User Story:** As a demo presenter, I want the Decider_Harness to apply the same guardrail, routing, confidence-gate, and confirmation flow as the Jev harness, so that the two implementations are behaviorally comparable turn for turn.

#### Acceptance Criteria

1. WHEN a user message is received, THE Decider_Harness SHALL evaluate the message for prompt injection using the Decider_Router's `is_injection` operation before routing.
2. IF the injection probability is greater than or equal to `0.80`, THEN THE Decider_Harness SHALL block the request, SHALL NOT invoke routing or reasoning, and SHALL return a response that indicates the request was blocked.
3. WHEN a user message passes the guardrail check, THE Decider_Harness SHALL obtain a Routing_Result from the Decider_Router's `route` operation using the Decider_Capability_Registry's capability descriptions.
4. WHERE the Routing_Result confidence is greater than or equal to `0.85`, THE Decider_Harness SHALL act on the selected capability immediately.
5. WHERE the Routing_Result confidence is between `0.50` and `0.85` exclusive of the upper bound used for act, THE Decider_Harness SHALL hold the selected capability as a pending confirmation and SHALL ask the user to confirm before acting.
6. WHERE the Routing_Result confidence is less than `0.50`, THE Decider_Harness SHALL escalate by asking the user for clarification and SHALL NOT act on any capability.
7. WHEN a pending confirmation exists and the next user reply, normalized, exactly matches one of the fast-path confirmation words `{"yes", "y", "yeah", "yep", "confirm", "confirmed", "sure", "ok", "okay", "do it", "go ahead", "proceed", "correct"}` or decline words `{"no", "n", "nope", "cancel", "stop", "nevermind", "never mind"}`, THE Decider_Harness SHALL resolve the confirmation in code without invoking the Decider_Router.
8. WHEN a pending confirmation exists and the next user reply does not match a fast-path word, THE Decider_Harness SHALL resolve the confirmation using the Decider_Router's `confirms` operation to obtain a confirm probability.
9. WHERE the confirm probability obtained from the Decider_Router's `confirms` operation is greater than or equal to `0.70`, THE Decider_Harness SHALL clear the pending confirmation and act on the pending capability.
10. WHERE the confirm probability obtained from the Decider_Router's `confirms` operation is less than or equal to `0.30`, THE Decider_Harness SHALL clear the pending confirmation and SHALL NOT act on the pending capability.
11. WHERE the confirm probability obtained from the Decider_Router's `confirms` operation is greater than `0.30` and less than `0.70`, THE Decider_Harness SHALL re-ask the user to confirm and SHALL retain the pending confirmation.
12. WHEN the Decider_Harness acts on the `llm_reasoning` capability, THE Decider_Harness SHALL delegate text generation to the Reasoning_Provider.
13. WHEN the Decider_Harness acts on a deterministic capability (`reset_password` or `unlock_account`), THE Decider_Harness SHALL execute the corresponding registered function without invoking the Reasoning_Provider.

### Requirement 5: Offline/Stubbed Decider Mode

**User Story:** As a booth presenter, I want an offline Strands Decider mode with no model weights or network dependency, so that I can demo or test the Decider_Harness without downloading the 2B parameter model.

#### Acceptance Criteria

1. THE Decider_Harness folder SHALL provide a Fake_Decider_Router that implements the same `route`, `is_injection`, and `confirms` operations as the Decider_Router using deterministic, keyword-based logic.
2. THE Fake_Decider_Router SHALL require no network access and no local model weights to operate.
3. WHEN the Decision_Mode environment variable is unset or set to the documented offline value (for example `offline`), THE System SHALL construct the Fake_Decider_Router for use by the Decider_Harness.
4. THE Fake_Decider_Router SHALL produce, for the scripted demo prompts defined in Requirement 7, Routing_Result outputs that select the same capability and the same Confidence_Gate band (act, clarify, or escalate) as the existing `FakeJev` produces for the same prompts.
5. THE Fake_Decider_Router SHALL produce, for the scripted demo prompts defined in Requirement 7, `is_injection` outputs that classify each prompt as a prompt-injection attempt or not a prompt-injection attempt consistently with the classification the existing `FakeJev.is_injection` produces for the same prompts.
6. THE Fake_Decider_Router SHALL produce, for the scripted demo prompts defined in Requirement 7, `confirms` outputs that classify each scripted confirmation reply as confirming, declining, or ambiguous consistently with the classification the existing `FakeJev.confirms` produces for the same reply.

### Requirement 6: Real Strands Decider Mode

**User Story:** As a developer evaluating Strands Decider, I want a real mode that loads and calls the actual strands-decider model, so that I can see genuine model-driven decisions rather than stubbed ones.

#### Acceptance Criteria

1. THE Decider_Harness folder SHALL provide a Real_Decider_Router that loads and invokes the `strands-decider` model to implement the `route`, `is_injection`, and `confirms` operations.
2. THE Real_Decider_Router SHALL defer importing its model-loading dependencies until a Real_Decider_Router instance is constructed, so that constructing or using the Fake_Decider_Router, and importing the Decider_Harness router module, do not require the `strands-decider` package or model weights to be installed.
3. WHEN the Decision_Mode is set to the documented value designating real/local behavior, THE System SHALL construct the Real_Decider_Router for use by the Decider_Harness.
4. IF the Real_Decider_Router cannot load the configured model (for example due to missing dependencies or missing weights), THEN THE System SHALL raise a descriptive error identifying the missing dependency or model id before any `route`, `is_injection`, or `confirms` operation is attempted, and SHALL leave the Decider_Harness without a constructed Real_Decider_Router.
5. THE Real_Decider_Router SHALL accept a configurable model identifier via a documented environment variable, and SHALL fall back to a single documented default Strands Decider model id (for example `StrandsAgents/strands-decider-2B-hobson-v19`) when that environment variable is unset.

### Requirement 7: Side-by-Side Comparison Runner

**User Story:** As a developer comparing decision providers, I want to run the same scripted prompts through both the Jev harness and the Decider_Harness, so that I can compare routing decisions, confidence, path taken, and latency directly.

#### Acceptance Criteria

1. THE System SHALL provide a Comparison_Runner, implemented as a script or an extended demo entry point, that is separate from the unmodified `demo.py` behavior described in Requirement 2.
2. THE Comparison_Runner SHALL execute a fixed, ordered set of exactly four scripted prompts: one deterministic high-confidence request, one open-ended reasoning request, one prompt-injection attempt, and one low-confidence/ambiguous request.
3. WHEN the Comparison_Runner processes a scripted prompt, THE Comparison_Runner SHALL run that prompt against both the existing Jev-based harness and the Decider_Harness.
4. THE Comparison_Runner SHALL report, for every scripted prompt and for each of the two harnesses, the selected capability or block/escalate path, the confidence score, the path taken (deterministic code, reasoning, guardrail block, or escalate/clarify), and the measured wall-clock latency of the decision step.
5. THE Comparison_Runner SHALL output the Jev harness result and the Decider_Harness result for the same scripted prompt adjacent to each other and grouped by that prompt (for example a side-by-side table row or a paired JSON block per prompt), such that the two results for one prompt never appear separated by the results of a different prompt.
6. THE Comparison_Runner SHALL support running against the offline/stubbed routers of both implementations with no network access and no model weights required.
7. WHERE the Comparison_Runner is configured to use real routers for one or both implementations, THE Comparison_Runner SHALL report latency measurements taken from the real decision calls.
8. IF running a scripted prompt against one harness raises an error or fails to produce a result, THEN THE Comparison_Runner SHALL record that harness's result for that prompt as a failure indicating which harness and prompt failed, and SHALL continue executing the remaining scripted prompts against both harnesses.

### Requirement 8: Comparison Documentation

**User Story:** As a developer or stakeholder evaluating both approaches, I want documentation describing the two decision-layer implementations and how to run each, so that I can understand the tradeoffs without reading all the source code.

#### Acceptance Criteria

1. THE System SHALL provide a single comparison document, located at either a file within the Decider_Harness folder or a top-level file in the repository root, describing both the Jev-based approach and the Strands Decider-based approach.
2. THE comparison document SHALL describe the typed-decision provider used by each approach, identifying the hosted TypeSafe API for the Jev-based approach and the local open-weight model for the Strands Decider-based approach.
3. THE comparison document SHALL describe the authentication/access model of each approach, stating that the Jev-based approach requires an API key and the Strands Decider-based approach requires no API key and runs local inference.
4. THE comparison document SHALL describe the latency characteristics of each approach by citing or quoting the figures or statements published in each provider's own documentation, with a reference to the source for each figure or statement.
5. THE comparison document SHALL describe the licensing distinction between the two approaches, identifying the Jev-based approach as a hosted proprietary service and the Strands Decider-based approach as open-source model weights.
6. THE comparison document SHALL include, for each value of Decision_Mode supported by the Decider_Harness (including at minimum an offline mode and a real/live mode), a runnable command, any required prerequisite configuration or credentials, and the expected observable output.
7. THE comparison document SHALL include, for running the Comparison_Runner, a runnable command, any required prerequisite configuration or credentials, and the expected observable output.
8. THE System SHALL NOT alter the existing content of `README.md` or `scripted_runs.md` for the Jev-only demo, consistent with Requirement 2.
