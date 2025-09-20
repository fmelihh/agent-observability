import logging
from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


# --- Setup Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("llm_agent")

# --- Setup Tracing ---
resource = Resource.create({"service.name": "llm-agent"})
provider = TracerProvider(resource=resource)
processor = BatchSpanProcessor(ConsoleSpanExporter())  # send to console (or Jaeger)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("llm_agent_tracer")

# --- Setup Metrics (Prometheus) ---
reader = PrometheusMetricReader()
meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("llm_agent_meter")

# Define metrics
request_latency = meter.create_histogram(
    "llm_request_latency_seconds", unit="s", description="Latency of LLM requests"
)
tokens_in_counter = meter.create_counter(
    "llm_tokens_in", description="Number of input tokens"
)
tokens_out_counter = meter.create_counter(
    "llm_tokens_out", description="Number of output tokens"
)
error_counter = meter.create_counter(
    "llm_errors", description="Number of errors during LLM execution"
)


__all__ = [
    "tracer",
    "request_latency",
    "tokens_in_counter",
    "tokens_out_counter",
    "error_counter",
]
