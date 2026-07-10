"""Reviewer Agent construction.

Performs policy compliance check using predefined rules.
"""

from __future__ import annotations

from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END

from config import Config


# 1. Define Graph State
class LegalState(TypedDict):
    text_to_check: str
    is_safe: bool
    fail_reason: str


def build_agent(cfg: Config) -> Any:
    # 2. Node: Simple Check Rule
    def compliance_check_node(state: LegalState) -> dict[str, Any]:
        forbidden_words = ["guaranteed profit", "risk-free", "absolute certainty"]
        text = state["text_to_check"].lower()

        for word in forbidden_words:
            if word in text:
                return {"is_safe": False, "fail_reason": f"Contains illegal marketing phrase: '{word}'"}

        return {"is_safe": True, "fail_reason": ""}

    # 3. Assemble LangGraph State Graph
    workflow = StateGraph(LegalState)
    workflow.add_node("check_policy", compliance_check_node)
    
    workflow.add_edge(START, "check_policy")
    workflow.add_edge("check_policy", END)
    
    return workflow.compile()
