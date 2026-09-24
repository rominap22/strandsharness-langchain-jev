"""
LangChain as the reasoning provider inside the Strands harness.

The Strands agent is model-driven: it wants a model with a system prompt.
Here the *model* is a LangChain chat model (Bedrock by default via langchain-aws).
Jev decides WHEN to invoke it; when it does, LangChain does the generation.

Swap the provider by changing one import/constructor:
  langchain-aws       -> ChatBedrockConverse   (default, Strands booth)
  langchain-openai    -> ChatOpenAI
  langchain-anthropic -> ChatAnthropic
"""
from __future__ import annotations

import os


class LangChainReasoner:
    """Bedrock-backed reasoner (default 'live' provider, Strands booth story)."""

    def __init__(self) -> None:
        from langchain_aws import ChatBedrockConverse  # lazy import

        self._llm = ChatBedrockConverse(
            model=os.getenv("BEDROCK_MODEL_ID",
                            "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
            region_name=os.getenv("AWS_REGION", "us-west-2"),
            temperature=0.2,
        )

    def reason(self, user_message: str, system_prompt: str) -> str:
        from langchain_core.messages import HumanMessage, SystemMessage

        resp = self._llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=user_message)]
        )
        return resp.content if isinstance(resp.content, str) else str(resp.content)


class FakeReasoner:
    """Offline stand-in so the reasoning branch works with no network."""

    def reason(self, user_message: str, system_prompt: str) -> str:  # noqa: ARG002
        return (
            "[FAKE reasoner -- offline mode] For SSO that works initially but fails after "
            "the OAuth access token expires, investigate: (1) refresh-token rotation and "
            "whether the client actually requests a new token, (2) token audience/scope "
            "mismatch on refresh, (3) IdP session lifetime vs. access-token lifetime, and "
            "(4) token caching that serves a stale, expired token."
        )


def make_reasoner():
    """
    Factory keyed on DEMO_MODE:
      offline (default)  -> FakeReasoner      (canned, no network)
      adapter | live     -> LangChainReasoner  (real answers via Bedrock)
    Both real modes reason on Bedrock; they differ only in the decision layer
    (adapter = System One adapter on Bedrock, live = real Jev).
    """
    mode = os.getenv("DEMO_MODE", "offline").lower()
    if mode in ("live", "adapter"):
        return LangChainReasoner()
    return FakeReasoner()
