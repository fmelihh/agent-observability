import time
import random
from fastapi import FastAPI

from agent_observability import trace

fastapi_app = FastAPI(
    title="Agent Observability",
)


@fastapi_app.get("/")
async def root():
    return {"message": "Hello World"}


@fastapi_app.get("/external-api-call")
def call_external_api():
    with trace.tracer.start_as_current_span("external_api_call") as span:
        start = time.time()
        try:
            # fake external API call
            time.sleep(random.uniform(0.1, 0.5))
            result = "Weather in Paris: Sunny, 22°C"

            # record metrics
            duration = time.time() - start
            trace.api_latency.record(duration)
            trace.api_calls_counter.add(1)

            span.set_attribute("api.result", result)
            return result
        except Exception as e:
            span.record_exception(e)
            raise


@fastapi_app.get("/external-api-high-latency")
def call_external_api_high_latency():
    with trace.tracer.start_as_current_span("external_api_call") as span:
        start = time.time()
        try:
            # fake external API call
            time.sleep(random.randint(15, 40))
            result = "Weather in Paris: Sunny, 22°C"

            # record metrics
            duration = time.time() - start
            trace.api_latency.record(duration)
            trace.api_calls_counter.add(1)

            span.set_attribute("api.result", result)
            return result
        except Exception as e:
            span.record_exception(e)
            raise
