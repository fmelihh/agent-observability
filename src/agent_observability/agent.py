import time
import httpx
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from agent_observability import trace  # your OTel setup


# --- Define State for LangGraph ---
class AgentState(TypedDict):
    input: str
    llm_output: str
    final_answer: str


# --- Tool Node: Real Weather API ---
async def get_weather(city: str) -> str:
    with trace.tracer.start_as_current_span("tool.get_weather") as span:
        start = time.time()
        try:
            # Very simple hardcoded city mapping for demo
            coords = {
                "paris": (48.8566, 2.3522),
                "london": (51.5074, -0.1278),
                "new york": (40.7128, -74.0060),
            }
            lat, lon = coords.get(city.lower(), (48.8566, 2.3522))  # default Paris

            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&current_weather=true"
            )

            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                data = resp.json()
                current = data.get("current_weather", {})
                result = (
                    f"The weather in {city.title()} is {current.get('temperature')}°C, "
                    f"windspeed {current.get('windspeed')} km/h."
                )

            # record API latency metric
            duration = time.time() - start
            trace.api_latency.record(duration, {"tool": "get_weather"})

            span.set_attribute("tool.city", city)
            span.set_attribute("tool.result", result)
            return result
        except Exception as e:
            trace.error_counter.add(1, {"tool": "get_weather"})
            span.record_exception(e)
            raise


# --- LLM Node with System Prompt ---
async def llm_node(state: AgentState) -> AgentState:
    with trace.tracer.start_as_current_span("llm.prompt_execution") as span:
        # Add system prompt here
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        user_input = state["input"]

        try:
            start = time.time()

            # Provide system + user roles
            response = llm.invoke(
                [
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. "
                        "If a query is about weather, respond with TOOL:city. "
                        "Otherwise, answer directly.",
                    },
                    {"role": "user", "content": user_input},
                ]
            )

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
            state["final_answer"] = await get_weather(city)
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
