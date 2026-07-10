"""FastAPI entrypoint for the Writer Agent.

Implements standard endpoints: ``POST /generate`` for drafting and compliance checking,
and ``GET /health`` for health checks.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from agent import build_agent
from config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("writer-agent")

CONFIG = Config.from_env()
AGENT = build_agent(CONFIG)
log.info("Writer Agent ready")

app = FastAPI(title="Writer Agent", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "agent": "writer"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = AGENT.invoke(
            {"messages": [HumanMessage(content=req.message)], "draft": "", "final_status": ""}
        )
        response_text = f"Draft Created:\n{result['draft']}\n\n{result['final_status']}"
        return ChatResponse(
            response=response_text,
            session_id=req.session_id
        )
    except Exception as exc:
        log.exception("agent invocation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
