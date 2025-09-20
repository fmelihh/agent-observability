import time
import random
import dotenv
import prometheus_client
from typing import Callable
from pydantic import BaseModel
from fastapi import FastAPI, Request, Body
from contextlib import asynccontextmanager

from agent_observability import trace, agent


class AgentInputDTO(BaseModel):
    query: str


fastapi_app = FastAPI(
    title="Agent Observability",
)

dotenv.load_dotenv()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    prometheus_client.start_http_server(9464)

    yield


@fastapi_app.middleware("http")
async def observability_middleware(request: Request, call_next: Callable):
    start_time = time.time()

    # Create a span for the request
    with trace.tracer.start_as_current_span("http_request") as span:
        try:
            response = await call_next(request)
        except Exception as e:
            # Record exception in span
            span.record_exception(e)
            raise

        # Duration
        duration = time.time() - start_time

        # ---- Add Span Attributes ----
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.duration_ms", duration * 1000)

        # ---- Record Metrics ----
        labels = {
            "method": request.method,
            "route": request.url.path,
            "status_code": response.status_code,
        }
        trace.request_latency.record(duration, labels)
        trace.request_counter.add(1, labels)

        return response


@fastapi_app.get("/")
async def root():
    return {"message": "Hello World"}


@fastapi_app.get("/external-api-call")
def call_external_api():
    time.sleep(random.randint(1, 5))
    return "External API call was triggered."


@fastapi_app.get("/external-api-high-latency")
def call_external_api_high_latency():
    time.sleep(random.randint(30, 50))
    return "External API call with high latency was triggered."


@fastapi_app.post("/agent-call")
async def agent_call(agent_input: AgentInputDTO = Body(...)):
    with trace.tracer.start_as_current_span("agent.request") as span:
        span.set_attribute("user.query", agent_input.query)
        app_graph = await agent.build_graph()
        result = await app_graph.ainvoke({"input": agent_input.query})
        answer = result.get("final_answer", "")

        span.set_attribute("agent.response", answer)
        return {"query": agent_input.query, "response": answer}
