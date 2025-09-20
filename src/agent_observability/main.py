import uvicorn
from prometheus_client import start_http_server

from agent_observability import app


def run_api():
    start_http_server(9464)

    uvicorn.run(app.fastapi_app, host="0.0.0.0", port=8000)
