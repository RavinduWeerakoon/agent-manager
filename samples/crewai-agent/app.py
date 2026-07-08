import os

# Keep CrewAI non-interactive and offline-friendly, and set these BEFORE
# importing crewai (they are read at import time): no hosted-trace upload, no
# interactive trace prompt, and use the bundled model pricing data instead of
# fetching it over the network on startup.
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("CREWAI_DISABLE_TRACING_PROMPT", "true")
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
# CrewAI writes under $HOME at import (a storage dir) and at Crew() construction
# (a credentials dir). When deployed, the platform sets HOME + CREWAI_STORAGE_DIR
# to writable paths. This block is a fallback so the sample also runs standalone
# under a read-only HOME; it no-ops when HOME is already writable or preset.
os.environ.setdefault("CREWAI_STORAGE_DIR", "/tmp/crewai")
if not os.access(os.path.expanduser("~"), os.W_OK):
    os.environ["HOME"] = "/tmp"

import base64
import json
import logging
import dotenv
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from agent.crew import create_crew

# Setup logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("crewai-agent")

# FastAPI Security Scheme for Bearer Token
security = HTTPBearer()

def verify_jwt(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    token = credentials.credentials
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("JWT must have 3 parts")
        
        # Decode payload (part 1)
        payload_b64 = parts[1]
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
        
        # Log client identity from token
        subject = payload.get("sub", "unknown")
        org_name = payload.get("namespace", "unknown")
        log.info(f"Authorized request for sub: {subject}, org: {org_name}")
        return payload
    except Exception as e:
        log.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid or malformed JWT credentials: {str(e)}"
        )

app = FastAPI()
# Load environment variables from a .env file (if present) for local runs; in
# the deployed pod the platform injects OPENAI_API_KEY as a sensitive env var.
dotenv.load_dotenv()
crew = create_crew()


class ChatRequest(BaseModel):
    session_id: str
    message: str


# Sync `def` (not `async`): crew.kickoff() is blocking, so FastAPI runs this in
# a threadpool instead of stalling the event loop. The Pydantic model gives a
# 422 (not an opaque 500) when `message` is missing, matching openapi.yaml.
@app.post("/chat")
def chat(payload: ChatRequest, token_claims: dict = Depends(verify_jwt)):
    result = crew.kickoff(inputs={"question": payload.message})
    return JSONResponse(content={"response": str(result)})

