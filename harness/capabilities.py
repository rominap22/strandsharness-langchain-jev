"""
Capability registry. Tool descriptions ARE Jev's decision space (Choice criteria).
Add a capability here and it automatically becomes a routing candidate -- no router
rewrite (the article's "capabilities describe themselves" point).

CODE = CONTROL: deterministic workflows run here with zero LLM cost.
"""
from __future__ import annotations

TOOLS: dict[str, dict] = {}


def register(name: str, description: str):
    def deco(func):
        TOOLS[name] = {"description": description, "function": func}
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


def jev_choices() -> dict[str, str]:
    """Build Jev's Choice criteria from the registry."""
    return {name: cfg["description"] for name, cfg in TOOLS.items()}
