"""FastAPI entrypoint for the Writer Agent.

Implements standard endpoints: ``POST /generate`` for drafting and compliance checking,
and ``GET /health`` for health checks.
"""

import json
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langchain_core.callbacks import AsyncCallbackHandler
from pydantic import BaseModel
from typing import Any
import logging
from fastapi.middleware.cors import CORSMiddleware

from agent import build_agent
from config import Config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("writer-agent")

CONFIG = Config.from_env()
AGENT = build_agent(CONFIG)
log.info("Writer Agent ready")

app = FastAPI(title="Writer Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TokenStreamHandler(AsyncCallbackHandler):
    def __init__(self):
        self.queue = asyncio.Queue()

    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        await self.queue.put(token)

    async def on_llm_end(self, *args, **kwargs) -> None:
        await self.queue.put(None)

    async def on_llm_error(self, *args, **kwargs) -> None:
        await self.queue.put(None)


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


@app.post("/chat")
async def chat(req: ChatRequest, request: Request) -> Any:
    is_stream = "text/event-stream" in request.headers.get("accept", "")
    handler = TokenStreamHandler()

    async def run_agent() -> Any:
        try:
            config = {"callbacks": [handler]}
            result = await AGENT.ainvoke(
                {"messages": [HumanMessage(content=req.message)], "draft": "", "final_status": ""},
                config=config
            )
            return result
        except Exception as exc:
            log.exception("agent invocation failed")
            await handler.queue.put(None)
            return None

    task = asyncio.create_task(run_agent())

    if is_stream:
        async def event_generator():
            while True:
                token = await handler.queue.get()
                if token is None:
                    break
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
            
            result = await task
            if result:
                status_text = result.get('final_status', '')
                if "APPROVED" in status_text:
                    yield f"data: {json.dumps({'type': 'status', 'content': 'APPROVED'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'content': status_text})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'status', 'content': 'Error: Agent execution failed.'})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")
    else:
        result = await task
        if not result:
            raise HTTPException(status_code=500, detail="Agent invocation failed")
        
        status_text = result.get('final_status', '')
        if "APPROVED" in status_text:
            response_text = result['draft']
        else:
            response_text = f"Draft Created:\n{result['draft']}\n\n{status_text}"

        return ChatResponse(
            response=response_text,
            session_id=req.session_id
        )
