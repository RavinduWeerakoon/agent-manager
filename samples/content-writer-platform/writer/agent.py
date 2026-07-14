"""LangGraph Writer Agent construction.

Generates draft content and coordinates compliance checks with the Reviewer Agent.
"""

from typing import Annotated, Any, TypedDict
import httpx

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import Config


# 1. Define Graph State
class WriterState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    draft: str
    final_status: str


def build_agent(cfg: Config) -> Any:
    # 2. Setup LLM with streaming enabled
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=cfg.openai_api_key,
        streaming=True
    )

    # 3. Node: Generate Draft (Async with Config propagation)
    async def write_draft_node(state: WriterState, config: RunnableConfig) -> dict[str, Any]:
        prompt = f"Write a short, professional product announcement about: {state['messages'][-1].content}"
        response = await llm.ainvoke([HumanMessage(content=prompt)], config=config)
        return {"draft": response.content}

    # 4. Node: Send to Reviewer Agent (Agent B) via Gateway (Async)
    async def send_to_legal_node(state: WriterState) -> dict[str, Any]:
        if not cfg.wso2_gateway_url:
            return {
                "final_status": "Compliance Result: REJECTED. Reason: WSO2 Gateway URL not configured."
            }

        headers = {"Authorization": f"Bearer {cfg.agent_b_auth_token}"}
        payload = {"message": state["draft"]}

        try:
            # Cross-app communication through Gateway boundary
            async with httpx.AsyncClient() as client:
                response = await client.post(cfg.wso2_gateway_url, headers=headers, json=payload, timeout=10.0)
            if response.status_code == 200:
                compliance_result = response.json()
                final_status = compliance_result.get("response", "Compliance Result: REJECTED. Reason: Empty response.")
            else:
                final_status = f"Compliance Result: REJECTED. Reason: Gateway returned status code {response.status_code}."
        except Exception as e:
            final_status = f"Compliance Result: REJECTED. Reason: Gateway communication failed: {str(e)}"

        return {"final_status": final_status}

    # 5. Assemble LangGraph State Graph
    workflow = StateGraph(WriterState)
    workflow.add_node("write_draft", write_draft_node)
    workflow.add_node("send_to_legal", send_to_legal_node)

    workflow.add_edge(START, "write_draft")
    workflow.add_edge("write_draft", "send_to_legal")
    workflow.add_edge("send_to_legal", END)
    
    return workflow.compile()
