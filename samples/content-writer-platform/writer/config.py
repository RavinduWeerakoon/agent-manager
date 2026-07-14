"""Configuration for the Writer Agent (Agent A).

Reads configurations from environment variables for LLM usage and gateway routing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return val


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    wso2_gateway_url: str
    agent_b_auth_token: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            openai_api_key=_env("OPENAI_API_KEY"),
            wso2_gateway_url=_env("WSO2_GATEWAY_URL", ""),
            agent_b_auth_token=_env("AGENT_B_AUTH_TOKEN", ""),
        )
