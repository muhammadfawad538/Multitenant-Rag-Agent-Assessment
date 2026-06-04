# Agentic QA Service — Take-Home Assessment (Section B)

A production-grade, highly optimized, and robust "Agentic QA" service built in **Python 3.10+** that dynamically plans, selects, and executes live tools (DuckDuckGo search and a Weather service) to answer user questions. 

This service returns a grounded, cited, and strictly structured JSON response while tracking detailed millisecond latency and token consumption metrics.

---

## 🌟 Key Features

* **Custom ReAct Planning Loop**: Designed and built entirely from scratch in native Python and the Anthropic SDK. Avoids heavy and opaque frameworks (like LangChain) to demonstrate complete control over agent routing, parsing, and execution.
* **Contract-First Design**: Powered by strict **Pydantic** models enforcing precise data contracts for all inputs, tool arguments, and output schemas.
* **True Parallel Tool Execution**: Orchestrates multiple independent tool executions concurrently using `asyncio.gather`, cutting execution latency in half compared to sequential agent loops.
* **Live Network Resilience**: Integrates exponential backoff and jitter retries via the `tenacity` library, and enforces strict HTTP timeouts on external requests to prevent hanging threads.
* **Flexible Run Modes**: 
  * **CLI Mode** for instant query results directly in the terminal.
  * **API Server Mode** running an asynchronous **FastAPI** application with a RESTful `/api/query` endpoint and automated CORS support.
  * **Dockerized** with multi-stage build optimization and structured container healthchecks.

---

## 🚀 Quick Start

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Install Dependencies
Create a virtual environment and install the required production and test libraries:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Configure Secrets
Copy the environment template and insert your Anthropic API Key:
```bash
cp .env.example .env
```
Open the `.env` file and set your key:
```env
ANTHROPIC_API_KEY=your-api-key-here
```

---

## 💻 Usage

### Running via CLI
Execute natural language queries directly from your terminal:
```bash
python -m src.main --query "What is the weather in Tokyo, and what is the latest news there?"
```

#### Example Output:
```json
=== Agent Response ===
{
  "answer": "The weather in Tokyo is Sunny and 27°C with a humidity of 70%. In other news, the historic new landmark Tokyo Skytree is hosting its annual spring broadcasting festival starting today (Source: [Tokyo Skytree](https://en.wikipedia.org/wiki/Tokyo_Skytree)).",
  "sources": [
    {
      "name": "Weather in Tokyo",
      "url": "https://weather.com"
    },
    {
      "name": "Tokyo Skytree",
      "url": "https://en.wikipedia.org/wiki/Tokyo_Skytree"
    }
  ],
  "latency_ms": {
    "total": 920.5,
    "by_step": {
      "planner": 450.2,
      "tool_execution": 120.1,
      "generation": 350.2
    }
  },
  "tokens": {
    "prompt": 540,
    "completion": 145
  }
}
```

### Running the API Server
Launch the FastAPI web server locally:
```bash
python -m src.main --server
```
The server will start at `http://localhost:8000`. 

#### API Endpoints:
* **POST `/api/query`**: Executes agent loop.
  * Request Body: `{"query": "Is it raining in Paris?"}`
  * Response: A structured JSON matching the `AgentOutput` schema.
* **GET `/health`**: Returns system health status and registered tools.

---

## 🐳 Docker Deployment

To build and run the entire service inside an isolated production-grade Docker container, run the provided script:
```bash
# Make script executable (macOS/Linux)
chmod +x run.sh

# Build and run
./run.sh
```
The script will automatically detect your local `ANTHROPIC_API_KEY` env variable, inject it into the container, map port `8000`, and start the FastAPI server.

---

## 🧪 Test-Driven Development (TDD)

This system was built following a strict **Test-Driven Development (TDD)** workflow. Every module was implemented by first writing failing unit and integration tests, then writing the minimum code required to make them pass, and finally refactoring for performance and clarity.

### Running the Tests
To run all tests (with detailed execution stats and coverage):
```bash
pytest -s
```

### TDD Design Highlights:
1. **Hermetic Testing (Network Isolation)**:
   * Unit tests must never query live external APIs, which leads to flaky tests, rate-limiting, or failures in offline CI pipelines.
   * We utilized `pytest-httpx` and `httpx_mock` to mock all external DuckDuckGo HTTP requests. Tests run 100% locally and instantly.
2. **Parallel Concurrency Verification**:
   * To prove the agent actually executes multiple tools in parallel (rather than using sequential `await` statements), we wrote `test_agent_concurrency_parallel_execution`.
   * The test registers two slow mock tools that sleep for 100ms each. When run, it asserts that the total tool execution latency is strictly `< 150ms` (proving parallel execution) instead of `>= 200ms` (sequential).
3. **Resilience & Fault Tolerance Testing**:
   * We wrote tests simulating "unhappy paths", such as tool server crashes (mocking a `500 Internal Server Error` or complete connection timeout).
   * We verified that the agent handles these errors gracefully, notifies the LLM of the failure, and still successfully synthesizes the best possible answer using the remaining active tools instead of crashing the system.

---

## 🛠️ Architecture & Implementation Choices

### 1. Handcrafted Core Loop (Custom Planner)
We deliberately chose not to use high-level, generic abstractions like LangChain or Index. While excellent for simple prototypes, they add hidden dependencies, make latency tracking difficult, and increase token consumption.
* **Our Approach**: We built a direct, transparent state machine. The LLM acts as the planner and router. We supply our tool definitions as standard JSON schemas dynamically generated from Pydantic. The agent executes the tools and passes the results back to the LLM for final generation.

### 2. Parallelism & Concurrency (Latency Reduction)
Latency is the single greatest bottleneck in production AI agent systems.
* **Our Approach**: When the planner selects multiple tool calls, we execute them concurrently using `asyncio.gather`. In a real-world query like "Check weather in Chicago, London, and Tokyo", the tool execution time is capped at the speed of the *slowest single call*, rather than the *sum of all calls*.

### 3. Production-Grade Network Reliability
* **Exponential Backoff**: We used the `tenacity` library to retry transient network drops (like `httpx.ConnectError` or `httpx.TimeoutException`) using exponential backoff with jitter. This prevents slamming the target servers during outages.
* **Timeouts**: We enforced a strict 5.0-second total timeout on all outbound HTTP calls. A slow weather or search API will never hang our API gateway or cause a thread block.
