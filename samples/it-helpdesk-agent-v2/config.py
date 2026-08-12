"""Instance-level configuration, read from env at startup.

Set ``USE_LLM_PROVIDER=true`` to route through the AM LLM provider
(with guardrails) using ``LLM_PROVIDER_URL`` and ``LLM_PROVIDER_KEY``.
By default (``false``), calls OpenAI directly using ``OPENAI_API_KEY``.

Set ``USE_MCP=true`` to additionally load tools from an MCP proxy using
``GITHUB_URL`` and ``GITHUB_API_KEY``. By default (``false``), only the
in-process tools are used and the agent behaves exactly as v1.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


@dataclass(frozen=True)
class Config:
    company_name: str
    tone: str
    max_tickets_per_query: int
    additional_guidance: str
    agent_version: str
    use_llm_provider: bool
    llm_provider_url: str
    llm_provider_key: str
    use_mcp: bool
    mcp_url: str
    mcp_api_key: str

    @classmethod
    def from_env(cls) -> "Config":
        raw_max_tickets = _env("MAX_TICKETS_PER_QUERY", "20")
        try:
            max_tickets = int(raw_max_tickets)
        except ValueError:
            raise RuntimeError(
                f"MAX_TICKETS_PER_QUERY must be an integer, got: {raw_max_tickets!r}"
            ) from None

        use_llm_provider = _env("USE_LLM_PROVIDER", "false").lower() == "true"
        llm_provider_url = _env("LLM_PROVIDER_URL", "")
        llm_provider_key = _env("LLM_PROVIDER_KEY", "")

        if use_llm_provider:
            if not llm_provider_url:
                raise RuntimeError(
                    "USE_LLM_PROVIDER is true but LLM_PROVIDER_URL is not set"
                )
            if not llm_provider_key:
                raise RuntimeError(
                    "USE_LLM_PROVIDER is true but LLM_PROVIDER_KEY is not set"
                )

        # AM injects <PROXY>_URL and <PROXY>_API_KEY when an MCP proxy named
        # "GitHub" is attached to the agent. Same shape as the LLM provider pair
        # above: system-managed, per environment, read-only in the console.
        use_mcp = _env("USE_MCP", "false").lower() == "true"
        mcp_url = _env("GITHUB_URL", "")
        mcp_api_key = _env("GITHUB_API_KEY", "")

        if use_mcp:
            if not mcp_url:
                raise RuntimeError("USE_MCP is true but GITHUB_URL is not set")
            if not mcp_api_key:
                raise RuntimeError("USE_MCP is true but GITHUB_API_KEY is not set")

        return cls(
            company_name=_env("COMPANY_NAME", "AcmeCorp"),
            tone=_env("TONE", "professional and helpful"),
            max_tickets_per_query=max_tickets,
            additional_guidance=_env("ADDITIONAL_GUIDANCE", ""),
            # Echoed in /health and every chat response so a promotion or a
            # rollback is visible from the outside without reading the console.
            agent_version=_env("AGENT_VERSION", "dev"),
            use_llm_provider=use_llm_provider,
            llm_provider_url=llm_provider_url,
            llm_provider_key=llm_provider_key,
            use_mcp=use_mcp,
            mcp_url=mcp_url,
            mcp_api_key=mcp_api_key,
        )
