"""Reviewer Agent construction.

Performs brand and compliance check using LLM evaluation.
"""

from __future__ import annotations

from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from config import Config


# 1. Define Graph State
class LegalState(TypedDict):
    text_to_check: str
    is_safe: bool
    fail_reason: str


def build_agent(cfg: Config) -> Any:
    # 2. Setup LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.0,
        api_key=cfg.openai_api_key
    )

    class ReviewResult(BaseModel):
        is_safe: bool = Field(
            description="True if the text complies with all brand guidelines. False if it violates any rules (contains XYZ, PQR, or uses incorrect tone/audience style)."
        )
        fail_reason: str = Field(
            description="If is_safe is False, provide a clear explanation of what failed and how it should be corrected. If is_safe is True, keep this empty."
        )

    structured_llm = llm.with_structured_output(ReviewResult)

    # 3. Node: LLM Brand Check Node
    async def compliance_check_node(state: LegalState) -> dict[str, Any]:
        prompt = f"""You are a Brand Compliance Reviewer for "ABC Company".
Target Audience: Small Business Owners.
Brand Voice: Professional yet conversational, empathetic, and authoritative.
Tone Thresholds: Never be overly formal or stuffy. Never use cheap internet slang. Always sound empathetic and authoritative.
Forbidden Competitor Keywords: XYZ, PQR. We must never name these competitors directly. If they are referenced, they must be called "traditional alternatives".

Review the following drafted content:
---
{state["text_to_check"]}
---

Check for forbidden competitor keywords (XYZ, PQR), proper tone (not stuffy, no cheap slang), and alignment with the target audience (Small Business Owners).
"""
        try:
            result = await structured_llm.ainvoke([HumanMessage(content=prompt)])
            return {
                "is_safe": result.is_safe,
                "fail_reason": result.fail_reason
            }
        except Exception as e:
            # Fallback check if LLM call fails
            text = state["text_to_check"].lower()
            for word in ["xyz", "pqr"]:
                if word in text:
                    return {
                        "is_safe": False,
                        "fail_reason": f"Contains forbidden competitor keyword: '{word}'"
                    }
            return {
                "is_safe": True,
                "fail_reason": ""
            }

    # 4. Assemble LangGraph State Graph
    workflow = StateGraph(LegalState)
    workflow.add_node("check_policy", compliance_check_node)
    
    workflow.add_edge(START, "check_policy")
    workflow.add_edge("check_policy", END)
    
    return workflow.compile()

