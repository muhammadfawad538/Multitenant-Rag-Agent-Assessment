import argparse
import asyncio
import os
import sys
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

from src.models import AgentOutput
from src.registry import ToolRegistry
from src.tools.weather import get_weather, WeatherInput
from src.tools.web_search import search_duckduckgo, SearchInput
from src.agent import Agent

# Initialize FastAPI App
app = FastAPI(
    title="Agentic QA Service API",
    description="A production-grade Agentic QA service that dynamically selects and runs live tools to answer queries.",
    version="1.0.0"
)

# Enable CORS for production robustness
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize and populate the Tool Registry
registry = ToolRegistry()

registry.register(
    name="get_weather",
    description="A dummy weather provider that returns realistic weather forecast, temperature (celsius/fahrenheit), condition, and humidity for any city location.",
    input_schema=WeatherInput,
    func=get_weather
)

registry.register(
    name="search_duckduckgo",
    description="A live web search tool that queries DuckDuckGo and returns standard search snippets, page titles, and source URLs. Use this for general fact-checking, news, and search queries.",
    input_schema=SearchInput,
    func=search_duckduckgo
)

# Initialize the core Agent Planner
global_agent = Agent(registry=registry)

# Define request schemas
class QueryRequest(BaseModel):
    query: str = Field(description="The natural language question/query to answer", min_length=1)

@app.post("/api/query", response_model=AgentOutput)
async def query_agent(payload: QueryRequest):
    """POST endpoint to query the Agent. Returns structured answers, sources, latencies, and token counts."""
    # Ensure GOOGLE_API_KEY is available when running in production/live mode
    if not os.environ.get("GOOGLE_API_KEY") and not app.extra.get("testing"):
        raise HTTPException(
            status_code=500,
            detail="Google API key is not configured. Please set the GOOGLE_API_KEY environment variable."
        )

    try:
        result = await global_agent.run(payload.query)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent failed to execute: {str(e)}"
        )

@app.get("/health")
def health_check():
    """Simple health check endpoint for monitoring."""
    return {"status": "healthy", "tools_registered": list(registry.tools.keys())}


def run_cli():
    """CLI runner to execute queries directly from the terminal."""
    parser = argparse.ArgumentParser(description="Agentic QA Service CLI")
    parser.add_argument(
        "--query",
        type=str,
        help="The query/question you want to ask the agent."
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run the FastAPI API server instead of a single query."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", 8000)),
        help="The port to run the FastAPI server on (default: 8000)."
    )

    args = parser.parse_args()

    if args.server or not args.query:
        # Start FastAPI Server
        print(f"Starting API Server on http://0.0.0.0:{args.port}...")
        uvicorn.run("src.main:app", host="0.0.0.0", port=args.port, reload=True)
    else:
        # Run CLI Query
        query = args.query.strip()
        if not query:
            print("Error: Query cannot be empty.")
            sys.exit(1)

        print(f"Planning and executing tools for query: '{query}'...")

        if not os.environ.get("GOOGLE_API_KEY"):
            print("WARNING: GOOGLE_API_KEY environment variable not found. Request may fail.")

        # Execute query synchronously from async loop
        async def main_cli():
            agent_result = await global_agent.run(query)
            # Print output as a pretty JSON block conforming to contract
            import json
            print("\n=== Agent Response ===")
            print(json.dumps(agent_result.model_dump(), indent=2))

        asyncio.run(main_cli())


if __name__ == "__main__":
    run_cli()
