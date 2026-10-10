from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from sre.integrations.prometheus import query_prometheus
from sre.tools.context import ToolContext


class PrometheusArguments(BaseModel):
    query: str = Field(description="PromQL query.")
    start: str | None = Field(default=None, description="Optional RFC3339 or Unix start time.")
    end: str | None = Field(default=None, description="Optional RFC3339 or Unix end time.")
    step: str = Field(default="60s", description="Range query step.")


@tool(args_schema=PrometheusArguments)
def query_metrics(
    query: str,
    start: str | None,
    end: str | None,
    step: str,
    runtime: ToolRuntime[ToolContext],
) -> dict:
    """Query the configured Prometheus server for alert, metric, or recovery evidence."""

    return query_prometheus(runtime.context.settings.prometheus.url, query, start, end, step)
