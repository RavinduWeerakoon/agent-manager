# IT Helpdesk Agent (v2)

An L1 IT helpdesk agent for the fictional **AcmeCorp**. Employees ask it to reset
passwords, request software, check ticket status, look up outages, and find which
source code repository owns a service. It is the running sample used throughout the
[Agent Manager tutorial series](https://wso2.github.io/agent-manager/docs/tutorials/create-your-first-agent).

Built with LangGraph (`create_react_agent`) on FastAPI, serving the Agent Manager
chat contract: `POST /chat` on port `8000`.

## What's different from v1

`samples/it-helpdesk-agent` is the minimal version — nine in-process tools over
mock JSON, and nothing else. v2 keeps all of that and adds what the tutorial
series needs:

| Change | Why |
|---|---|
| `USE_MCP` toggle loading tools from an MCP proxy | Chapter 3 connects the agent to GitHub through an Agent Manager MCP proxy |
| Known-issue triage rules in the system prompt | The agent checks the IT team's issue tracker before opening a ticket, and may only read it |
| Session memory (LangGraph checkpointer) | Multi-turn "verify me, then act" flows genuinely work; v1 discarded history between turns |
| `AGENT_VERSION` echoed in `/health` and every chat response | Makes a promotion or rollback visible from the outside |
| `scripts/seed_traffic.py` | Generates enough traces for a monitor to score |

With `USE_MCP=false` (the default), v2 behaves like v1 plus session memory.

## Configuration

All configuration is environment variables. Only the LLM credential is required.

| Variable | Default | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | — | Required unless `USE_LLM_PROVIDER=true` |
| `COMPANY_NAME` | `AcmeCorp` | Used in the system prompt |
| `TONE` | `professional and helpful` | Used in the system prompt |
| `ADDITIONAL_GUIDANCE` | *(empty)* | Extra prompt text appended verbatim |
| `MAX_TICKETS_PER_QUERY` | `20` | Caps ticket listings |
| `AGENT_VERSION` | `dev` | Echoed in `/health` and chat responses |
| `USE_LLM_PROVIDER` | `false` | Route through an Agent Manager LLM Service Provider |
| `LLM_PROVIDER_URL` / `LLM_PROVIDER_KEY` | — | Injected by Agent Manager; required when `USE_LLM_PROVIDER=true` |
| `USE_MCP` | `false` | Load tools from an MCP proxy in addition to the in-process ones |
| `GITHUB_URL` / `GITHUB_API_KEY` | — | Injected by Agent Manager when an MCP proxy named `GitHub` is attached; required when `USE_MCP=true` |

`LLM_PROVIDER_*` and `GITHUB_*` are **system-managed** — Agent Manager writes them
per environment and they are read-only in the console. You never paste an upstream
OpenAI or GitHub credential into the agent.

## Run it locally

```bash
python -m venv env && source env/bin/activate
pip install -r requirements.txt

export OPENAI_API_KEY=sk-...
python main.py
```

Then:

```bash
curl -s localhost:8000/health

curl -s localhost:8000/chat -H 'Content-Type: application/json' -d '{
  "session_id": "demo-1",
  "message": "I need my password reset. alice.chen@acmecorp.com, E-1001."
}'
```

Reuse the same `session_id` across calls to continue a conversation. Omit it and
each request starts its own.

### Seeding traffic

```bash
python scripts/seed_traffic.py --url http://localhost:8000
```

Runs twelve scripted conversations — a deliberate mix of requests that should
succeed and requests that should be refused, so an evaluator has both to score.
Add `--api-key` when the endpoint is secured, and `--only <name>` to run one.

## Test data

Mock data lives in `data/` and resets on restart; nothing is persisted.

- **Employees** — `E-1001` … `E-1010`. `E-1004`, `E-1006`, `E-1009`, `E-1010` are
  admin accounts, which the agent must refuse to reset and escalate instead.
- **Policies** — `POL-IT-001` … `POL-IT-008`, covering password resets, software
  access, escalation, privacy, and after-hours support.
- **Tickets**, **software catalog**, **system status** — supporting fixtures.

Useful for exercising the rules: `alice.chen@acmecorp.com` / `E-1001` is a normal
Engineering account; `david.kim@acmecorp.com` / `E-1004` is an admin account.

## Layout

```
agent.py               LLM binding, system prompt, MCP tool loading, checkpointer
app.py                 FastAPI app — /chat and /health
config.py              Environment configuration
main.py                Entrypoint (python main.py)
tools.py               The nine in-process tools
clients/               Mock backends behind the tools
data/                  Mock JSON fixtures
scripts/seed_traffic.py  Scripted conversations for seeding traces
```

## Deploying it

The tutorial series covers deployment, model governance, MCP tools, evaluation,
and promotion to production, in that order. Start at
[Create Your First Agent](https://wso2.github.io/agent-manager/docs/tutorials/create-your-first-agent).
