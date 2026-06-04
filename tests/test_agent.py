import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent import Agent
from src.models import AgentOutput
from src.registry import ToolRegistry
from src.tools.weather import get_weather, WeatherInput
from src.tools.web_search import search_duckduckgo, SearchInput

@pytest.fixture
def mock_registry():
    registry = ToolRegistry()
    registry.register(
        name="get_weather",
        description="Get weather for a location",
        input_schema=WeatherInput,
        func=get_weather
    )
    registry.register(
        name="search_duckduckgo",
        description="Search web using DuckDuckGo",
        input_schema=SearchInput,
        func=search_duckduckgo
    )
    return registry

@pytest.mark.asyncio
async def test_agent_output_schema_validation(mock_registry):
    """Test that the agent returns a valid AgentOutput conforming to our Pydantic schema."""
    with patch('src.agent.genai') as mock_genai:
        # Mock the Gemini API calls
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()

        # Mock Gemini response with function calls
        mock_part = MagicMock()
        mock_part.function_call.name = "get_weather"
        mock_part.function_call.args = {"location": "Tokyo", "unit": "celsius"}

        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]
        mock_response.text = "According to the weather tool, it is Sunny in Tokyo today."

        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model

        # Mock environment variable for API key
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            # Initialize agent with mocked Gemini client
            agent = Agent(registry=mock_registry)

            # Run query
            result = await agent.run("What is the weather in Tokyo?")

            # Assert contract compliance
            assert isinstance(result, AgentOutput)
            assert result.answer is not None
            assert result.latency_ms.total > 0
            assert "planner" in result.latency_ms.by_step
            assert "tool_execution" in result.latency_ms.by_step
            assert "generation" in result.latency_ms.by_step

@pytest.mark.asyncio
async def test_agent_concurrency_parallel_execution(mock_registry):
    """Test that multiple independent tools chosen by the planner are run in parallel."""
    # We will create two slow mock tools and register them
    slow_registry = ToolRegistry()

    async def slow_tool_1(query: str):
        await asyncio.sleep(0.1)  # Sleep 100ms
        return {"result": "slow 1 done"}

    async def slow_tool_2(query: str):
        await asyncio.sleep(0.1)  # Sleep 100ms
        return {"result": "slow 2 done"}

    class DummyInput(MagicMock):
        pass

    slow_registry.register("slow1", "slow tool 1", SearchInput, slow_tool_1)
    slow_registry.register("slow2", "slow tool 2", SearchInput, slow_tool_2)

    with patch('src.agent.genai') as mock_genai:
        # Mock Gemini API calls for concurrent tool execution
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()

        # Mock two function calls in the response
        mock_part1 = MagicMock()
        mock_part1.function_call.name = "slow1"
        mock_part1.function_call.args = {"query": "test"}

        mock_part2 = MagicMock()
        mock_part2.function_call.name = "slow2"
        mock_part2.function_call.args = {"query": "test"}

        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part1, mock_part2]
        mock_response.text = "Both slow tools successfully executed in parallel."

        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model

        # Mock environment variable for API key
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            # Initialize agent
            agent = Agent(registry=slow_registry)

            # Run agent
            start_time = time.perf_counter()
            result = await agent.run("Run both slow tools")
            end_time = time.perf_counter()

            duration_ms = (end_time - start_time) * 1000

            # If execution was sequential, it would take >= 200ms of sleep alone.
            # Since they run in parallel, the tool execution step should take ~100ms.
            # Allow some buffer for CPU/event-loop overhead.
            tool_exec_latency = result.latency_ms.by_step.get("tool_execution", 0)
            assert tool_exec_latency < 180  # Must be parallel!
            assert result.latency_ms.total > 0

@pytest.mark.asyncio
async def test_agent_graceful_tool_failure(mock_registry):
    """Test that the agent handles tool failures gracefully without crashing."""
    # We will register a tool that raises a ConnectionError or exception
    failing_registry = ToolRegistry()

    async def broken_tool(query: str):
        raise ValueError("API is down")

    failing_registry.register("broken", "broken tool", SearchInput, broken_tool)

    with patch('src.agent.genai') as mock_genai:
        # Mock Gemini API calls
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()

        # Mock function call for broken tool
        mock_part = MagicMock()
        mock_part.function_call.name = "broken"
        mock_part.function_call.args = {"query": "test"}

        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [mock_part]
        mock_response.text = "I tried to search but the search tool was unavailable. However, here is what I can tell you..."

        mock_chat.send_message_async = AsyncMock(return_value=mock_response)
        mock_model.start_chat.return_value = mock_chat
        mock_genai.GenerativeModel.return_value = mock_model

        # Mock environment variable for API key
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test_key'}):
            # Initialize agent
            agent = Agent(registry=failing_registry)

            # The run should complete successfully despite the tool failure
            result = await agent.run("Search something on broken tool")
            assert isinstance(result, AgentOutput)
            assert result.answer is not None
