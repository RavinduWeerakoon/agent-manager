"""Configuration for the Reviewer Agent (Agent B).

Reads configurations from environment variables.
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

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            openai_api_key=_env("OPENAI_API_KEY", ""),
        )
