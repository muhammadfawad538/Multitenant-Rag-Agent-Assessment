import pytest
import os
# Mock Anthropic key for hermetic test execution
os.environ["ANTHROPIC_API_KEY"] = "mock-key-for-testing"

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from src.models import AgentOutput, Source, LatencyMS, TokenUsage

client = TestClient(app)

@pytest.fixture
def mock_agent_output():
    return AgentOutput(
        answer="This is a mocked answer with citations. [Source: Weather in Tokyo](https://weather.com)",
        sources=[Source(name="Weather in Tokyo", url="https://weather.com")],
        latency_ms=LatencyMS(
            total=100.0,
            by_step={"planner": 30.0, "tool_execution": 50.0, "generation": 20.0}
        ),
        tokens=TokenUsage(prompt=120, completion=45)
    )

@patch("src.main.global_agent")
def test_query_endpoint_success(mock_global_agent, mock_agent_output):
    """Test that the /api/query POST endpoint returns structured AgentOutput on success."""
    # Setup mock agent run to return our mocked output
    mock_run = AsyncMock(return_value=mock_agent_output)
    mock_global_agent.run = mock_run

    payload = {"query": "What is the weather in Tokyo?"}
    response = client.post("/api/query", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert "answer" in json_data
    assert "sources" in json_data
    assert "latency_ms" in json_data
    assert "tokens" in json_data
    assert json_data["answer"] == mock_agent_output.answer
    assert json_data["sources"][0]["name"] == "Weather in Tokyo"
    assert json_data["latency_ms"]["total"] == 100.0

def test_query_endpoint_missing_payload():
    """Test that the /api/query endpoint rejects invalid input payloads."""
    # Send empty payload
    response = client.post("/api/query", json={})
    assert response.status_code == 422  # Unprocessable Entity

    # Send payload with wrong key
    response = client.post("/api/query", json={"question": "Tokyo"})
    assert response.status_code == 422
