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
    with trace.tracer.start_as_current_span("external_api_call"):
        time.sleep(random.uniform(0.1, 0.5))
        return "Weather in Paris: Sunny, 22°C"
