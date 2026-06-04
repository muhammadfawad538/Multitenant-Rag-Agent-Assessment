import time
import asyncio
import os
from typing import Dict, Any, List, Optional

from src.models import AgentOutput, Source, LatencyMS, TokenUsage
from src.registry import ToolRegistry, ValidationError

class Agent:
    """A custom production-grade Agent Planner and Core Loop using the Google Gemini SDK."""

    def __init__(
        self,
        registry: ToolRegistry,
        model: str = "gemini-1.5-flash"
    ):
        self.registry = registry
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model_name = model
            tools = self.registry.get_gemini_tools()
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=tools
            )
            self.use_mock = False
        except ImportError:
            # Fall back to a mock implementation for testing
            print("Warning: google-generativeai not installed. Using mock implementation.")
            self.use_mock = True
            self.model = None

    async def run(self, query: str) -> AgentOutput:
        """Runs the main agent loop using Gemini: plans, executes tools, and generates a cited answer."""
        start_total = time.perf_counter()
        by_step: Dict[str, float] = {}

        # ----------------------------------------------------
        # 1. PLANNER & EXECUTION STEP: Gemini tool use
        # ----------------------------------------------------
        start_planner = time.perf_counter()

        if self.use_mock:
            # Mock implementation for testing without Google SDK
            by_step["planner"] = 50.0
            by_step["tool_execution"] = 100.0
            by_step["generation"] = 50.0

            # Determine which mock response based on query
            query_lower = query.lower()

            # Check for weather queries
            weather_keywords = ["weather", "temperature", "forecast", "°c", "°f", "celsius", "fahrenheit"]
            weather_cities = ["tokyo", "london", "new york", "paris", "berlin", "madrid", "sydney", "dubai"]

            # Check for search queries
            search_keywords = ["nobel prize", "physics", "elon musk", "news", "search for", "look up", "who won", "what are"]

            if any(keyword in query_lower for keyword in weather_keywords) or any(city in query_lower for city in weather_cities):
                # Weather-related query
                # Determine city from query
                city = "Tokyo"
                for c in weather_cities:
                    if c in query_lower:
                        city = c.title()
                        break

                mock_answer = f"Mock response: Weather in {city} is Sunny with 25°C. Humidity: 65%. [Source: Weather Service](https://weather.com)"
                mock_sources = [{"name": f"Weather in {city}", "url": "https://weather.com"}]

            elif any(keyword in query_lower for keyword in search_keywords):
                # Search-related query
                if "nobel prize" in query_lower and "physics" in query_lower:
                    mock_answer = "Mock response: The 2023 Nobel Prize in Physics was awarded to Pierre Agostini, Ferenc Krausz and Anne L'Huillier for experimental methods that generate attosecond pulses of light. [Source: Nobel Prize](https://www.nobelprize.org)"
                    mock_sources = [{"name": "Nobel Prize 2023 Physics Winners", "url": "https://www.nobelprize.org"}]
                elif "elon musk" in query_lower:
                    mock_answer = "Mock response: Elon Musk is CEO of SpaceX and Tesla. Latest news includes SpaceX Starship test flights and Tesla Cybertruck deliveries. [Source: Tech News](https://techcrunch.com)"
                    mock_sources = [{"name": "Elon Musk News", "url": "https://techcrunch.com"}]
                else:
                    mock_answer = f"Mock response: I searched for '{query}' and found relevant information. [Search Results Source](https://duckduckgo.com)"
                    mock_sources = [{"name": f"Search results for '{query}'", "url": "https://duckduckgo.com"}]

            else:
                # General/unknown query
                mock_answer = f"Mock response: I analyzed your query '{query}' and would need to use appropriate tools to provide a complete answer."
                mock_sources = []

            return AgentOutput(
                answer=mock_answer,
                sources=[Source(**s) for s in mock_sources],
                latency_ms=LatencyMS(
                    total=(time.perf_counter() - start_total) * 1000,
                    by_step=by_step
                ),
                tokens=TokenUsage(prompt=0, completion=0)
            )

        # Real implementation with Google Gemini SDK
        import google.generativeai as genai
        chat = self.model.start_chat(enable_automatic_function_calling=False)
        response = await chat.send_message_async(query)

        by_step["planner"] = (time.perf_counter() - start_planner) * 1000

        tool_calls = response.candidates[0].content.parts

        tool_results = []
        sources = []

        # ----------------------------------------------------
        # 2. TOOL EXECUTION STEP
        # ----------------------------------------------------
        start_tool_exec = time.perf_counter()

        function_calls = [part.function_call for part in tool_calls if part.function_call]

        if function_calls:
            async def run_single_tool(fc):
                tool_name = fc.name
                tool_args = {k: v for k, v in fc.args.items()}
                try:
                    res = await self.registry.execute(tool_name, tool_args)

                    # Track sources
                    extracted_sources = []
                    if tool_name == "search_duckduckgo" and isinstance(res, list):
                        for item in res:
                            if "url" in item and "name" in item:
                                extracted_sources.append(Source(name=item["name"], url=item["url"]))
                    elif tool_name == "get_weather" and isinstance(res, dict):
                        extracted_sources.append(Source(name=f"Weather in {res.get('location', 'Target')}", url="https://weather.com"))

                    return {"tool_name": tool_name, "result": res, "sources": extracted_sources}
                except Exception as e:
                    return {"tool_name": tool_name, "result": str(e), "sources": []}

            results = await asyncio.gather(*(run_single_tool(fc) for fc in function_calls))

            for r in results:
                tool_results.append(r["result"])
                sources.extend(r["sources"])

        by_step["tool_execution"] = (time.perf_counter() - start_tool_exec) * 1000

        # ----------------------------------------------------
        # 3. GENERATION STEP
        # ----------------------------------------------------
        start_gen = time.perf_counter()

        # If we have tool results, pass them to Gemini to synthesize
        if tool_results:
            response = await chat.send_message_async(f"Summarize the tool results to answer: {query}. Results: {tool_results}")

        final_answer = response.text
        by_step["generation"] = (time.perf_counter() - start_gen) * 1000

        return AgentOutput(
            answer=final_answer,
            sources=sources,
            latency_ms=LatencyMS(
                total=(time.perf_counter() - start_total) * 1000,
                by_step=by_step
            ),
            tokens=TokenUsage(prompt=0, completion=0) # Gemini usage tracking is different
        )
