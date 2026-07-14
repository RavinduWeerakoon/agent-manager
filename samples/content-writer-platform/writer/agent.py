"""LangGraph Writer Agent construction.

Generates content and coordinates compliance checks with the Reviewer Agent.
"""

from typing import Annotated, Any, TypedDict
import httpx

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from config import Config


# 1. Define Graph State
class WriterState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    draft: str
    final_status: str
    routing_decision: str       # "BYPASS" or "REVIEW"
    reviewer_feedback: str      # Holds criticism from reviewer agent


def build_agent(cfg: Config) -> Any:
    # 2. Setup LLM with streaming enabled
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=cfg.openai_api_key,
        streaming=True,
        max_tokens=300
    )

    class RoutingDecision(BaseModel):
        pipeline: str = Field(description="Must be either 'BYPASS' (Option A) or 'REVIEW' (Option B)")
        reason: str = Field(description="Brief reason for the decision")

    # 3. Node: Classify Request (Option A/B)
    async def classify_node(state: WriterState) -> dict[str, Any]:
        last_message = state["messages"][-1].content
        
        # Classifier LLM
        classifier_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=cfg.openai_api_key
        )
        structured_classifier = classifier_llm.with_structured_output(RoutingDecision)
        
        try:
            decision = await structured_classifier.ainvoke([
                HumanMessage(content=f"""Analyze the following user request and determine the correct agent pipeline:
User Request: "{last_message}"

Guidelines:
- Choose 'BYPASS' (Option A) if the request is purely structural (e.g., formatting, Markdown conversions, HTML tags), a simple formatting change, basic typo/SEO editing, or an initial brainstorming/ideation request (e.g., "give me ideas", "brainstorm titles").
- Choose 'REVIEW' (Option B) if the request involves drafting new public-facing content (e.g., blogs, product announcements, social posts, newsletters), direct promotional pitches, or tone-shifting existing copy.""")
            ])
            pipeline = decision.pipeline
        except Exception:
            # Fallback keyword checking
            pipeline = "REVIEW" if any(k in last_message.lower() for k in ["announcement", "blog", "post", "newsletter", "draft", "write", "pitch"]) else "BYPASS"
            
        return {"routing_decision": pipeline}

    # 4. Node: Option A - General Response (Bypasses Reviewer)
    async def write_general_response_node(state: WriterState, config: RunnableConfig) -> dict[str, Any]:
        last_message = state["messages"][-1].content
        
        prompt = f"""You are a helpful and polite AI writing assistant for the brand "ABC Company".
Target Audience: Small Business Owners.
Brand Voice: Professional yet conversational, empathetic, and authoritative.

Respond directly and concisely to the following request:
{last_message}"""
        
        callback = config.get("configurable", {}).get("token_callback") if config else None
        draft = ""
        async for chunk in llm.astream([HumanMessage(content=prompt)], config=config):
            draft += chunk.content
            if callback:
                await callback(chunk.content)
        return {"draft": draft, "final_status": "BYPASSED"}

    # 5. Node: Option B - Initial Draft Generation
    async def write_draft_node(state: WriterState, config: RunnableConfig) -> dict[str, Any]:
        last_message = state["messages"][-1].content
        
        prompt = f"""You are a professional Content Writer for the brand "ABC Company".
Target Audience: Small Business Owners.
Brand Voice: Professional yet conversational, empathetic, and authoritative.
Tone Thresholds: Never be overly formal or stuffy. Never use cheap internet slang. Always sound empathetic and authoritative.

Generate a high-quality initial draft based on the user's request:
{last_message}"""
        
        callback = config.get("configurable", {}).get("token_callback") if config else None
        draft = ""
        async for chunk in llm.astream([HumanMessage(content=prompt)], config=config):
            draft += chunk.content
            if callback:
                await callback(chunk.content)
        return {"draft": draft, "final_status": ""}

    # 6. Node: Send to Reviewer Agent via Gateway
    async def send_to_legal_node(state: WriterState) -> dict[str, Any]:
        if not cfg.wso2_gateway_url:
            return {
                "final_status": "Compliance Result: REJECTED. Reason: WSO2 Gateway URL not configured."
            }

        headers = {"Authorization": f"Bearer {cfg.agent_b_auth_token}"}
        payload = {"message": state["draft"]}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(cfg.wso2_gateway_url, headers=headers, json=payload, timeout=15.0)
            if response.status_code == 200:
                compliance_result = response.json()
                reviewer_msg = compliance_result.get("response", "")
                if "APPROVED" in reviewer_msg:
                    return {"final_status": "APPROVED", "reviewer_feedback": ""}
                else:
                    feedback = reviewer_msg.replace("Compliance Result: REJECTED. Reason: ", "").strip()
                    return {"final_status": "REJECTED", "reviewer_feedback": feedback}
            else:
                return {
                    "final_status": "REJECTED",
                    "reviewer_feedback": f"Gateway returned status code {response.status_code}."
                }
        except Exception as e:
            return {
                "final_status": "REJECTED",
                "reviewer_feedback": f"Gateway communication failed: {str(e)}"
            }

    # 7. Node: Option B - Rewrite Draft Node (when compliance check fails)
    async def rewrite_draft_node(state: WriterState, config: RunnableConfig) -> dict[str, Any]:
        last_message = state["messages"][-1].content
        original_draft = state["draft"]
        feedback = state["reviewer_feedback"]
        
        prompt = f"""You are a professional Content Writer for the brand "ABC Company".
You recently generated this draft:
---
{original_draft}
---

However, the Brand Compliance Reviewer flagged it with the following feedback:
"{feedback}"

Please rewrite the draft to fully address the feedback. Keep the good elements, but correct any violations (e.g. competitor mentions of XYZ/PQR, incorrect tone, stuffiness, internet slang).
Generate the polished final version. Ensure it complies with the guidelines.

After the rewritten content, append a separator and a "Reviewer Note" explaining briefly what was corrected.
Example format:
[Polished content here]

---
Reviewer Note: Corrected the mention of XYZ to traditional alternatives and adjusted the tone to sound more empathetic.
"""
        
        callback = config.get("configurable", {}).get("token_callback") if config else None
        if callback:
            await callback("[CLEAR]")
        draft = ""
        async for chunk in llm.astream([HumanMessage(content=prompt)], config=config):
            draft += chunk.content
            if callback:
                await callback(chunk.content)
        return {"draft": draft, "final_status": "APPROVED"}

    # 8. Assemble LangGraph State Graph
    workflow = StateGraph(WriterState)
    workflow.add_node("classify", classify_node)
    workflow.add_node("write_general", write_general_response_node)
    workflow.add_node("write_draft", write_draft_node)
    workflow.add_node("send_to_legal", send_to_legal_node)
    workflow.add_node("rewrite_draft", rewrite_draft_node)

    # Define edges and routing
    workflow.add_edge(START, "classify")

    def route_after_classify(state: WriterState) -> str:
        if state.get("routing_decision") == "BYPASS":
            return "write_general"
        return "write_draft"

    workflow.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "write_general": "write_general",
            "write_draft": "write_draft"
        }
    )

    workflow.add_edge("write_general", END)
    workflow.add_edge("write_draft", "send_to_legal")

    def route_after_review(state: WriterState) -> str:
        if state.get("final_status") == "APPROVED":
            return END
        return "rewrite_draft"

    workflow.add_conditional_edges(
        "send_to_legal",
        route_after_review,
        {
            END: END,
            "rewrite_draft": "rewrite_draft"
        }
    )

    workflow.add_edge("rewrite_draft", END)
    
    return workflow.compile()

