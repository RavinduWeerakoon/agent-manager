"""LangGraph Writer Agent construction.

Generates draft content and coordinates compliance checks with the Reviewer Agent.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict
import requests

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from config import Config


# 1. Define Graph State
class WriterState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    draft: str
    final_status: str


def build_agent(cfg: Config) -> Any:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7, api_key=cfg.openai_api_key)

    # 3. Node: Generate Draft
    def write_draft_node(state: WriterState) -> dict[str, Any]:
        prompt = f"Write a short, professional product announcement about: {state['messages'][-1].content}"
        response = llm.invoke([HumanMessage(content=prompt)])
        return {"draft": response.content}

    # 4. Node: Send to Reviewer Agent (Agent B) via Gateway
    def send_to_legal_node(state: WriterState) -> dict[str, Any]:
        if not cfg.wso2_gateway_url:
            return {
                "final_status": "Compliance Result: REJECTED. Reason: WSO2 Gateway URL not configured."
            }

        headers = {"Authorization": f"Bearer {cfg.agent_b_auth_token}"}
        payload = {"message": state["draft"]}

        try:
            # Cross-app communication through Gateway boundary
            response = requests.post(cfg.wso2_gateway_url, headers=headers, json=payload, timeout=10.0)
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
