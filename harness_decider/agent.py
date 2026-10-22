"""
The Strands Decider harness.

Structural mirror of harness/agent.py's SupportAgent: same guardrail -> route
-> confidence-gate -> confirmation flow, same thresholds, same deterministic-
code-vs-LLM-reasoning split. The only substitution is the typed-decision
provider: Strands Decider instead of Jev.

Thresholds and fast-path word sets are copied here as literal constants
(not imported from harness/agent.py) so the two harnesses stay independently
modifiable -- editing one must never risk changing the other's behavior.

The llm_reasoning capability still delegates to LangChain/Bedrock via
harness.lc_model.make_reasoner(), imported directly rather than re-implemented,
so there is exactly one LangChain/Bedrock wiring in the whole repository.
"""
from __future__ import annotations

from dataclasses import dataclass

from harness.lc_model import make_reasoner

from .capabilities import DECIDER_TOOLS, decider_choices
from .decider_router import RealDeciderRouter, make_decider_router

REASONING_SYSTEM_PROMPT = (
    "You are the reasoning component inside a hybrid IT-support agent. "
    "Answer clearly and concisely; do not invent account state."
)

HI_CONF = 0.85
LO_CONF = 0.50
INJECTION_BLOCK = 0.80

# Short confirmations the app resolves itself -- no need to re-route through
# the decider. ("don't ask AI to decide something your application already
# knows.") Copied as literals from harness/agent.py to keep the two harnesses
# decoupled.
CONFIRM_WORDS = {"yes", "y", "yeah", "yep", "confirm", "confirmed", "sure", "ok",
                 "okay", "do it", "go ahead", "proceed", "correct"}
DECLINE_WORDS = {"no", "n", "nope", "cancel", "stop", "nevermind", "never mind"}


@dataclass
class TurnResult:
    text: str
    path: str          # which branch fired (for the on-screen trace)
    used_llm: bool
    detail: dict        # raw decider output, for the demo's JSON panel


class DeciderHarness:
    """
    Strands Decider-backed counterpart to harness.agent.SupportAgent.

    Swap make_decider_router() for live vs offline, exactly as SupportAgent
    swaps make_jev().
    """

    def __init__(self) -> None:
        self.decider = make_decider_router()
        if isinstance(self.decider, RealDeciderRouter):
            # Fail fast: a bad model id or missing dependency surfaces at
            # harness construction time, not mid-conversation.
            self.decider._ensure_loaded()
        self.reasoner = make_reasoner()
        self.llm_calls = 0
        self.turns = 0
        self.pending_confirmation: tuple[str, str] | None = None  # (capability, original_message)

    def _act(self, choice: str, user_message: str, detail: dict) -> TurnResult:
        """Execute a resolved capability: code for deterministic, LangChain for reasoning."""
        if choice != "llm_reasoning":
            fn = DECIDER_TOOLS[choice]["function"]
            return TurnResult(text=fn(user_message), path="deterministic_code",
                              used_llm=False, detail=detail)
        answer = self.reasoner.reason(user_message, REASONING_SYSTEM_PROMPT)
        self.llm_calls += 1
        return TurnResult(text=answer, path="langchain_reasoning",
                          used_llm=True, detail=detail)

    def handle(self, user_message: str) -> TurnResult:
        self.turns += 1
        text_norm = user_message.strip().lower()

        # 0) Resolve a pending confirmation: fast-path obvious words in code,
        #    else ask the decider a typed yes/no Noul (natural language --
        #    no LLM, still sub-second).
        if self.pending_confirmation is not None:
            pending, original_msg = self.pending_confirmation
            if text_norm in CONFIRM_WORDS:
                self.pending_confirmation = None
                return self._act(pending, original_msg,
                                 {"resolved_confirmation": pending, "via": "fast-path"})
            if text_norm in DECLINE_WORDS:
                self.pending_confirmation = None
                return TurnResult(text="Okay, cancelled. What would you like instead?",
                                  path="confirmation_declined", used_llm=False,
                                  detail={"cancelled": pending, "via": "fast-path"})
            # Natural-language reply -> decider Noul decides confirm vs. not.
            confirm_p = self.decider.confirms(user_message, pending)
            if confirm_p >= 0.70:
                self.pending_confirmation = None
                return self._act(pending, original_msg,
                                 {"resolved_confirmation": pending,
                                  "confirm_probability": confirm_p, "via": "decider_noul"})
            if confirm_p <= 0.30:
                self.pending_confirmation = None
                return TurnResult(text="Okay, cancelled. What would you like instead?",
                                  path="confirmation_declined", used_llm=False,
                                  detail={"cancelled": pending,
                                          "confirm_probability": confirm_p, "via": "decider_noul"})
            # Genuinely ambiguous reply -> re-ask once, keep the pending action.
            return TurnResult(
                text=(f"Just to confirm — should I proceed with '{pending}'? "
                      "Reply yes or no."),
                path="confirmation_ambiguous", used_llm=False,
                detail={"pending": pending, "confirm_probability": confirm_p},
            )

        # 1) Guardrail (decider Noul) -- decider on the FRONT end.
        injection_p = self.decider.is_injection(user_message)
        if injection_p >= INJECTION_BLOCK:
            return TurnResult(
                text="That request was blocked by the input guardrail.",
                path="guardrail_block",
                used_llm=False,
                detail={"injection_probability": injection_p},
            )

        # 2) Route (decider Choice).
        decision = self.decider.route(user_message, decider_choices())
        detail = {
            "route": decision.choice,
            "confidence": decision.confidence,
            "probabilities": decision.probabilities,
            "injection_probability": injection_p,
        }

        # 3) Confidence gate.
        if decision.confidence < LO_CONF:
            return TurnResult(
                text="I'm not sure what you'd like me to do. Could you add a little detail?",
                path="escalate_low_confidence",
                used_llm=False,
                detail=detail,
            )
        if decision.confidence < HI_CONF:
            self.pending_confirmation = (decision.choice, user_message)
            return TurnResult(
                text=(f"Did you want me to '{decision.choice}'? "
                      "Reply 'yes' to proceed or 'no' to cancel."),
                path="clarify_medium_confidence",
                used_llm=False,
                detail=detail,
            )

        # 4) Act (high confidence).
        return self._act(decision.choice, user_message, detail)

    def stats(self) -> dict:
        return {"turns": self.turns, "llm_calls": self.llm_calls,
                "decided_without_llm": self.turns - self.llm_calls}
