import pytest
from src.tools.weather import get_weather, WeatherInput
from src.tools.web_search import search_duckduckgo, SearchInput
from src.registry import ValidationError
import httpx

# --- Weather Tool Tests ---

@pytest.mark.asyncio
async def test_weather_tool_valid():
    """Test that the weather tool returns realistic weather data for any location."""
    # Test valid input structure validation
    inputs = WeatherInput(location="Tokyo", unit="celsius")
    assert inputs.location == "Tokyo"
    assert inputs.unit == "celsius"

    # Test tool execution
    result = await get_weather(location="Tokyo", unit="celsius")
    assert "location" in result
    assert result["location"] == "Tokyo"
    assert "temperature" in result
    assert "condition" in result
    assert "humidity" in result
    assert "celsius" in result["unit"]

@pytest.mark.asyncio
async def test_weather_tool_default_unit():
    """Test weather tool default arguments."""
    result = await get_weather(location="New York")
    assert result["location"] == "New York"
    assert result["unit"] == "celsius"  # Default

# --- Web Search Tool Tests ---

@pytest.mark.asyncio
async def test_search_duckduckgo_success(httpx_mock):
    """Test search_duckduckgo with a successful mock HTTP response."""
    # Mock DuckDuckGo API response
    mock_url = "https://api.duckduckgo.com/?q=Tokyo&format=json&no_html=1"
    mock_response = {
        "AbstractText": "Tokyo is the capital and most populous city of Japan.",
        "AbstractURL": "https://en.wikipedia.org/wiki/Tokyo",
        "Heading": "Tokyo",
        "RelatedTopics": [
            {
                "Text": "Tokyo Skytree - A broadcasting and observation tower.",
                "FirstURL": "https://en.wikipedia.org/wiki/Tokyo_Skytree"
            }
        ]
    }

    httpx_mock.add_response(
        url=mock_url,
        json=mock_response,
        status_code=200
    )

    result = await search_duckduckgo(query="Tokyo")

    # Assert search returned expected parsed results
    assert len(result) >= 1
    assert result[0]["name"] == "Tokyo"
    assert "most populous city" in result[0]["snippet"]
    assert result[0]["url"] == "https://en.wikipedia.org/wiki/Tokyo"

    # Check that related topics were parsed if abstract is empty or as additional info
    assert any("Skytree" in r["name"] for r in result)
    assert any("broadcasting" in r["snippet"] for r in result)

@pytest.mark.asyncio
async def test_search_duckduckgo_empty_results(httpx_mock):
    """Test that search_duckduckgo handles empty results gracefully."""
    mock_url = "https://api.duckduckgo.com/?q=nonexistentquery&format=json&no_html=1"
    mock_response = {
        "AbstractText": "",
        "AbstractURL": "",
        "Heading": "",
        "RelatedTopics": []
    }

    httpx_mock.add_response(
        url=mock_url,
        json=mock_response,
        status_code=200
    )

    result = await search_duckduckgo(query="nonexistentquery")
    assert result == []

@pytest.mark.asyncio
async def test_search_duckduckgo_server_error(httpx_mock):
    """Test that search_duckduckgo raises a robust exception or handles server failures."""
    mock_url = "https://api.duckduckgo.com/?q=error&format=json&no_html=1"

    # Mock server error
    httpx_mock.add_response(
        url=mock_url,
        status_code=500
    )

    # We expect it to raise httpx.HTTPStatusError or a custom error we catch.
    # In production, we want retry logic or a clean failure.
    with pytest.raises(httpx.HTTPError):
        await search_duckduckgo(query="error")
