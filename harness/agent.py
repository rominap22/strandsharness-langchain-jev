"""
The Strands harness.

Strands is the orchestration loop. Inside each turn:
  1. Jev Noul guardrail on the raw input (block injections).
  2. Jev Choice router picks the capability (typed, ~100ms, confidence-scored).
  3. Confidence gate:  >=0.85 act | 0.5-0.85 clarify | <0.5 escalate.
  4. Deterministic capability -> code.  'llm_reasoning' -> LangChain model.

On a clarify, the chosen capability is held as pending state. The user's next reply is
resolved by a fast-path word check, then a typed Jev Noul ("does this confirm?") for
natural language -- no LLM call needed to understand "yeah, go ahead".

We register Jev as a Strands *tool* and LangChain as the Strands *model provider*,
so this file reads as ordinary Strands agent wiring.
"""
from __future__ import annotations

from dataclasses import dataclass

from .capabilities import TOOLS, jev_choices
from .jev_router import make_jev
from .lc_model import make_reasoner

REASONING_SYSTEM_PROMPT = (
    "You are the reasoning component inside a hybrid IT-support agent. "
    "Answer clearly and concisely; do not invent account state."
)

HI_CONF = 0.85
LO_CONF = 0.50
INJECTION_BLOCK = 0.80

# Short confirmations the app resolves itself -- no need to re-route through Jev.
# ("don't ask AI to decide something your application already knows.")
CONFIRM_WORDS = {"yes", "y", "yeah", "yep", "confirm", "confirmed", "sure", "ok",
                 "okay", "do it", "go ahead", "proceed", "correct"}
DECLINE_WORDS = {"no", "n", "nope", "cancel", "stop", "nevermind", "never mind"}


@dataclass
class TurnResult:
    text: str
    path: str          # which branch fired (for the on-screen trace)
    used_llm: bool
    detail: dict       # raw Jev output, for the demo's JSON panel


class SupportAgent:
    """Minimal Strands-style harness. Swap make_jev()/make_reasoner() for live vs offline."""

    def __init__(self) -> None:
        self.jev = make_jev()
        self.reasoner = make_reasoner()
        self.llm_calls = 0
        self.turns = 0
        self.pending_confirmation: tuple[str, str] | None = None  # (capability, original_message)

    def _act(self, choice: str, user_message: str, detail: dict) -> TurnResult:
        """Execute a resolved capability: code for deterministic, LangChain for reasoning."""
        if choice != "llm_reasoning":
            fn = TOOLS[choice]["function"]
            return TurnResult(text=fn(user_message), path="deterministic_code",
                              used_llm=False, detail=detail)
        answer = self.reasoner.reason(user_message, REASONING_SYSTEM_PROMPT)
        self.llm_calls += 1
        return TurnResult(text=answer, path="langchain_reasoning",
                          used_llm=True, detail=detail)

    def handle(self, user_message: str) -> TurnResult:
        self.turns += 1
        text_norm = user_message.strip().lower()

        # 0) Resolve a pending confirmation: fast-path obvious words in code, else ask
        #    Jev a typed yes/no Noul (natural language -- no LLM, still sub-second).
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
            # Natural-language reply -> Jev Noul decides confirm vs. not.
            confirm_p = self.jev.confirms(user_message, pending)
            if confirm_p >= 0.70:
                self.pending_confirmation = None
                return self._act(pending, original_msg,
                                 {"resolved_confirmation": pending,
                                  "confirm_probability": confirm_p, "via": "jev_noul"})
            if confirm_p <= 0.30:
                self.pending_confirmation = None
                return TurnResult(text="Okay, cancelled. What would you like instead?",
                                  path="confirmation_declined", used_llm=False,
                                  detail={"cancelled": pending,
                                          "confirm_probability": confirm_p, "via": "jev_noul"})
            # Genuinely ambiguous reply -> re-ask once, keep the pending action.
            return TurnResult(
                text=(f"Just to confirm — should I proceed with '{pending}'? "
                      "Reply yes or no."),
                path="confirmation_ambiguous", used_llm=False,
                detail={"pending": pending, "confirm_probability": confirm_p},
            )

        # 1) Guardrail (Jev Noul) -- Jev on the FRONT end.
        injection_p = self.jev.is_injection(user_message)
        if injection_p >= INJECTION_BLOCK:
            return TurnResult(
                text="That request was blocked by the input guardrail.",
                path="guardrail_block",
                used_llm=False,
                detail={"injection_probability": injection_p},
            )

        # 2) Route (Jev Choice).
        decision = self.jev.route(user_message, jev_choices())
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
