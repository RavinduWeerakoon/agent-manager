"""FastAPI entrypoint for the Reviewer Agent.

Implements standard endpoints: ``POST /review`` for compliance checking,
and ``GET /health`` for health checks.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from agent import build_agent
from config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("reviewer-agent")

CONFIG = Config.from_env()
AGENT = build_agent(CONFIG)
log.info("Reviewer Agent ready")

app = FastAPI(title="Reviewer Agent", version="0.1.0")


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str | None = None


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "agent": "reviewer"}


@app.post("/chat", response_model=ChatResponse)
async def review_document(
    req: ChatRequest,
    authorization: str = Header(None)
) -> ChatResponse:
    # Local fallback verification; WSO2 AI Gateway will handle primary validation
    if not authorization:
        raise HTTPException(status_code=401, detail="Unauthorized client access")

    initial_state = {
        "text_to_check": req.message,
        "is_safe": True,
        "fail_reason": ""
    }

    try:
        graph_output = await AGENT.ainvoke(initial_state)
        status = "APPROVED" if graph_output["is_safe"] else "REJECTED"
        reason = graph_output["fail_reason"] if not graph_output["is_safe"] else "Passed all checks."
        response_text = f"Compliance Result: {status}. Reason: {reason}"
        return ChatResponse(
            response=response_text,
            session_id=req.session_id
        )
    except Exception as exc:
        log.exception("agent invocation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
