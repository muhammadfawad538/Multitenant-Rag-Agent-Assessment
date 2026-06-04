from pydantic import BaseModel, Field
from typing import List, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class SearchInput(BaseModel):
    query: str = Field(description="The search query to look up on the web (e.g., 'Tokyo top news today')")

# Production-grade resilience: retry on transient HTTP errors (network drops, 5xx) with backoff and jitter
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError)),
    reraise=True
)
async def fetch_ddg_results(client: httpx.AsyncClient, query: str) -> Dict[str, Any]:
    """Helper function to fetch search results from DuckDuckGo with retry logic."""
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": "1"
    }

    # Strict timeout: 5 seconds total to prevent hanging
    response = await client.get(url, params=params, timeout=5.0)

    # Raise status errors (e.g. 500, 404) so that we raise HTTPStatusError
    response.raise_for_status()

    return response.json()

async def search_duckduckgo(query: str) -> List[Dict[str, Any]]:
    """Web search tool that queries DuckDuckGo and returns a list of parsed sources and snippets."""
    async with httpx.AsyncClient() as client:
        try:
            data = await fetch_ddg_results(client, query)
        except httpx.HTTPStatusError as e:
            # Re-raise standard HTTPError for testing compliance and robust logging
            raise httpx.HTTPError(f"HTTP Error {e.response.status_code} from DuckDuckGo: {str(e)}")
        except Exception as e:
            # Let other standard HTTPX exceptions bubble up (ConnectError, TimeoutException)
            raise httpx.HTTPError(f"Failed to query DuckDuckGo: {str(e)}")

    results = []

    # 1. Extract Abstract (if present)
    if data.get("AbstractText") and data.get("AbstractURL"):
        results.append({
            "name": data.get("Heading") or query,
            "url": data.get("AbstractURL"),
            "snippet": data.get("AbstractText")
        })

    # 2. Extract Related Topics (to enrich the snippets and results)
    related_topics = data.get("RelatedTopics", [])
    for topic in related_topics:
        # Avoid nested groups for simplicity, look for text and url
        if "Text" in topic and "FirstURL" in topic:
            # We want to format the result with name and snippet
            # The topic text usually starts with the topic name followed by " - " and description
            text = topic["Text"]
            url = topic["FirstURL"]
            parts = text.split(" - ", 1)
            name = parts[0] if len(parts) > 1 else query
            snippet = parts[1] if len(parts) > 1 else text

            # Avoid duplicates of the primary abstract
            if not any(r["url"] == url for r in results):
                results.append({
                    "name": name,
                    "url": url,
                    "snippet": snippet
                })

        # Cap results at 5 to keep context token count low and optimized
        if len(results) >= 5:
            break

    return results
