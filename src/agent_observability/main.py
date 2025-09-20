import uvicorn

from agent_observability import app


def run_api():
    uvicorn.run(app.fastapi_app, host="0.0.0.0", port=8000)
