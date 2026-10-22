# Jev vs. Strands Decider — comparing two typed-decision providers

This folder (`harness_decider/`) is a second, parallel implementation of the same
IT-support harness demo as `harness/`, using **Strands Decider** instead of **Jev**
as the typed-decision layer. The two implementations route the same three
capabilities (`reset_password`, `unlock_account`, `llm_reasoning`), apply the
same confidence-gate thresholds, and both delegate to the same LangChain/Bedrock
reasoning provider for open-ended questions.

Nothing in `harness/`, `demo.py`, `README.md`, or `scripted_runs.md` was changed
to add this. This document and `compare_demo.py` (repo root) are the only new
additions needed to run both side by side.

## The two approaches

| | Jev (`harness/`) | Strands Decider (`harness_decider/`) |
|---|---|---|
| **Decision provider** | [TypeSafe System One](https://docs.typesafe.ai) — a hosted model accessed via `POST /v1/systemone` | [`strands-decider-2b`](https://strandsagents.com/blog/introducing-strands-decider/) — a 2B-parameter, open-weight model you run locally |
| **Access / auth** | Requires a `TYPESAFE_API_KEY`; calls go over the network to TypeSafe's hosted endpoint | No API key. Runs local CPU/GPU inference via the `strands-decider` package; no network call for a decision |
| **Latency** | TypeSafe advertises typed decisions in roughly 70–500 ms per the Jev + LLMs article referenced in the main `README.md` | Strands' own announcement reports a median decision latency of about 115 ms on an Nvidia RTX 3090 and about 153 ms on an M3 MacBook, for small tasks, increasing roughly linearly with task size ([source](https://strandsagents.com/blog/introducing-strands-decider/)) |
| **Licensing** | Hosted, proprietary service (TypeSafe System One / Jev) | Open source. Code is on GitHub, weights are on Hugging Face, and the training data/scripts are published alongside the model |
| **Output shape** | Typed `Choice` (choice + probabilities + confidence) and `Noul` (single probability) | Same shape: a `Choice`-style best-of-N decision with probabilities/confidence, and a `Noul`-style yes/no probability |
| **What it can't do** | Can't generate free text; routes `llm_reasoning` to LangChain/Bedrock instead | Same limitation — it's explicitly a decision model, not a generator, so open-ended requests are routed to the same LangChain/Bedrock reasoning provider |

Both approaches follow the identical division of labor used throughout this repo:
**the decider picks/scores, the LLM reasons only when routed to.** Swapping Jev
for Strands Decider changes who makes the typed decision; it does not change
the harness's control flow, the capability set, or how `llm_reasoning` answers
are generated.

## Running the Strands Decider harness

### Offline mode (default, no dependencies, no network)

```bash
python3 -c "
from harness_decider import DeciderHarness
agent = DeciderHarness()
print(agent.handle('I forgot my password'))
"
```

Expected: a `TurnResult` with `path='deterministic_code'`, no network access, no
`strands-decider` package required. This is the default — `DECIDER_MODE` is
unset or `offline`.

### Real/live mode (actual strands-decider-2b model)

```bash
pip install strands-decider
export DECIDER_MODE=live
# Optional: override the default model id
export DECIDER_MODEL_ID=StrandsAgents/strands-decider-2B-hobson-v19

python3 -c "
from harness_decider import DeciderHarness
agent = DeciderHarness()
print(agent.handle('I forgot my password'))
"
```

Expected: the harness loads `strands-decider-2b` locally (first run downloads
weights from Hugging Face) and answers using the real model's typed decisions.
If the `strands-decider` package or weights are unavailable, construction fails
fast with a `RuntimeError` naming the missing dependency or model id, before any
turn is processed.

`strands-decider` is an optional dependency — it is not added to
`requirements.txt` as a hard requirement, consistent with how `typesafe_sdk` is
only needed for Jev's `live` mode today.

## Running the comparison

```bash
python3 compare_demo.py
```

Runs four fixed scripted prompts (a deterministic request, an open-ended
reasoning request, a prompt-injection attempt, and a low-confidence/ambiguous
request) through both `harness.SupportAgent` (Jev) and `harness_decider.DeciderHarness`
(Strands Decider), printing each prompt's two results — capability/path,
confidence, and measured decision latency — immediately next to each other.

Expected output: a header line naming both active router classes, four
`====`-delimited blocks (one per prompt) each with a `JEV` line and a `DECIDER`
line directly beneath it, and a final stats line per harness.

By default (`DEMO_MODE=offline`, `DECIDER_MODE=offline`) this requires no
network access and no model weights. To compare using the real models instead:

```bash
export DEMO_MODE=live            # real Jev (needs TYPESAFE_API_KEY)
export DECIDER_MODE=live         # real strands-decider-2b (needs the package + weights)
python3 compare_demo.py
```

Latency figures printed in that mode reflect the real decision calls rather
than the near-zero latency of the offline stubs.

## Sources

- Strands Decider announcement: [strandsagents.com/blog/introducing-strands-decider](https://strandsagents.com/blog/introducing-strands-decider/)
- Jev / TypeSafe System One docs: [docs.typesafe.ai](https://docs.typesafe.ai)
- Jev + LLMs: fast typed decisions plus generated language: [builder.aws.com article](https://builder.aws.com/content/3JgdW6BWEBxbMRp6LoJ6mjMoT64/jev-and-llms-fast-typed-decisions-plus-generated-language)
