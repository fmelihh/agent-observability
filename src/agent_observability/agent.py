import time
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from agent_observability import trace  # your OTel setup


# --- Define State for LangGraph ---
class AgentState(Dict[str, Any]):
    pass


# --- Tool Node ---
async def get_weather(city: str) -> str:
    with trace.tracer.start_as_current_span("tool.get_weather") as span:
        start = time.time()
        try:
            # Fake external API latency
            time.sleep(0.3)
            result = f"The weather in {city} is Sunny, 22°C."

            duration = time.time() - start
            trace.api_latency.record(duration, {"tool": "get_weather"})

            span.set_attribute("tool.city", city)
            span.set_attribute("tool.result", result)
            return result
        except Exception as e:
            trace.error_counter.add(1, {"tool": "get_weather"})
            span.record_exception(e)
            raise


# --- LLM Node ---
async def llm_node(state: AgentState) -> AgentState:
    with trace.tracer.start_as_current_span("llm.prompt_execution") as span:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        user_input = state["input"]

        try:
            start = time.time()
            response = llm.invoke(user_input)
            duration = time.time() - start

            # Token usage (if available)
            tokens_in = response.response_metadata.get("token_usage", {}).get(
                "prompt_tokens", 0
            )
            tokens_out = response.response_metadata.get("token_usage", {}).get(
                "completion_tokens", 0
            )
            trace.tokens_in_counter.add(tokens_in, {"model": "gpt-4o-mini"})
            trace.tokens_out_counter.add(tokens_out, {"model": "gpt-4o-mini"})

            # Trace attributes
            span.set_attribute("llm.model", "gpt-4o-mini")
            span.set_attribute("llm.prompt", user_input)
            span.set_attribute("llm.tokens_in", tokens_in)
            span.set_attribute("llm.tokens_out", tokens_out)
            span.set_attribute("llm.duration", duration)

            state["llm_output"] = response.content
            return state
        except Exception as e:
            trace.error_counter.add(1, {"component": "llm"})
            span.record_exception(e)
            raise


# --- Routing Node ---
async def weather_node(state: AgentState) -> AgentState:
    with trace.tracer.start_as_current_span("agent.routing") as span:
        output = state["llm_output"]
        if output.startswith("TOOL:"):
            city = output.split(":", 1)[1].strip()
            span.set_attribute("decision", "tool_call")
            state["final_answer"] = get_weather(city)
        else:
            span.set_attribute("decision", "direct_response")
            state["final_answer"] = output
        return state


# --- Build LangGraph Workflow ---


async def build_graph():
    workflow = StateGraph(AgentState)
    workflow.add_node("llm", llm_node)
    workflow.add_node("weather", weather_node)
    workflow.set_entry_point("llm")
    workflow.add_edge("llm", "weather")
    workflow.add_edge("weather", END)

    return workflow.compile()
