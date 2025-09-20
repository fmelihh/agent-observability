import time
import random
from typing import Callable
from fastapi import FastAPI, Request

from agent_observability import trace

fastapi_app = FastAPI(
    title="Agent Observability",
)


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
        trace.request_latency.record(duration)
        trace.api_calls_counter.add(
            1,
            {
                "method": request.method,
                "route": request.url.path,
                "status_code": response.status_code,
            },
        )

        return response


@fastapi_app.get("/")
async def root():
    return {"message": "Hello World"}


@fastapi_app.get("/external-api-call")
def call_external_api():
    time.sleep(random.uniform(0.1, 0.5))
    return "External API call was triggered."


@fastapi_app.get("/external-api-high-latency")
def call_external_api_high_latency():
    time.sleep(random.randint(15, 40))
    return "External API call with high latency was triggered."
