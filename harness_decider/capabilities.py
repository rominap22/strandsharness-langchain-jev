"""
Capability registry for the Strands Decider harness.

Mirrors harness/capabilities.py exactly in shape and content. Tool descriptions
ARE the Decider_Router's decision space (Choice/Noul criteria) -- add a
capability here and it automatically becomes a routing candidate, no router
rewrite.

CODE = CONTROL: deterministic workflows run here with zero model cost.

This module is independently maintained (not imported from harness/) so the
two harnesses stay fully decoupled, but the capability names and descriptions
are copied character-for-character from harness/capabilities.py so the two
decision layers are routing over an identical decision space.
"""
from __future__ import annotations

DECIDER_TOOLS: dict[str, dict] = {}


def register(name: str, description: str):
    def deco(func):
        DECIDER_TOOLS[name] = {"description": description, "function": func}
        return func
    return deco


@register(
    name="reset_password",
    description="The user forgot their password or wants to reset it.",
)
def reset_password(message: str) -> str:  # noqa: ARG001
    # Real impl would call Okta/Entra; here it's deterministic code, no model.
    return "Password reset workflow started. Check your registered email for a link."


@register(
    name="unlock_account",
    description="The user's account is locked and needs to be unlocked.",
)
def unlock_account(message: str) -> str:  # noqa: ARG001
    return "Account unlock workflow started. You'll be able to sign in shortly."


@register(
    name="llm_reasoning",
    description=(
        "The request needs explanation, analysis, comparison, troubleshooting, "
        "summarization, or open-ended reasoning that has no predefined answer."
    ),
)
def llm_reasoning(message: str) -> str:  # placeholder; agent injects the reasoner
    raise NotImplementedError("Routed to the LangChain model by the harness.")


def decider_choices() -> dict[str, str]:
    """Build the Decider_Router's Choice criteria from the registry."""
    return {name: cfg["description"] for name, cfg in DECIDER_TOOLS.items()}
