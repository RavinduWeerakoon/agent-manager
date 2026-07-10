from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel

from agent import build_agent
from config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("it-helpdesk")

raw_urls = os.environ.get("MY_PROXY_URL", "")
mcp_server_urls = [url.strip() for url in raw_urls.split(",") if url.strip()]
mcp_api_key = os.environ.get("MY_PROXY_API_KEY", "").strip()

server_configs: dict[str, dict[str, Any]] = {
    f"mcp_server_{i}": {
        "url": url,
        "transport": "streamable_http",
        "headers": {
            "API-Key": mcp_api_key,
            "Authorization": "",
        },
    }
    for i, url in enumerate(mcp_server_urls)
} if mcp_server_urls and mcp_api_key else {}

# Define an async function to handle the asynchronous operations
async def initialize_tools():
    if not server_configs:
        return []
    try:
        log.info("Initializing MCP tools from servers...")
        mcp_client = MultiServerMCPClient(server_configs)
        tools = await asyncio.wait_for(mcp_client.get_tools(), timeout=5.0)
        log.info("MCP tools initialized successfully.")
        return tools
    except Exception as exc:
        log.warning("Failed to initialize MCP tools: %s. Falling back to empty tools list.", exc)
        return []

tools = asyncio.run(initialize_tools())

CONFIG = Config.from_env()
AGENT = build_agent(CONFIG)
log.info(
    "IT helpdesk agent ready (company=%s, tone=%s, llm_provider=%s)",
    CONFIG.company_name,
    CONFIG.tone,
    "agent-manager" if CONFIG.use_llm_provider else "openai-direct",
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    context: dict[str, Any] | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str | None = None


app = FastAPI(title="IT Helpdesk Agent", version="0.1.0")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "company": CONFIG.company_name}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = AGENT.invoke({"messages": [HumanMessage(content=req.message)]})
    except Exception as exc:  # noqa: BLE001
        log.exception("agent invocation failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    final: Any = None
    for m in reversed(result.get("messages", [])):
        if isinstance(m, AIMessage):
            final = m.content
            break
    if final is None:
        final = "(no response)"
    if isinstance(final, list):
        final = "\n".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in final
        )
    final = str(final.strip()) + str(tools)  # Append tools information to the response
    return ChatResponse(response=str(final), session_id=req.session_id)
