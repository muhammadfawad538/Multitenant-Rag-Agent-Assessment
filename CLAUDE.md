# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
This repository contains the deliverables for the **Take-Home AI Engineer Assessment**, which includes:
- **Section A (Architecture)**: System design for a multitenant, production-grade RAG + Agentic system.
- **Section B (Coding)**: A production-minded "Agentic QA" service built in Python 3.10+ that dynamically selects and runs live tools (DuckDuckGo Search and a Weather dummy tool) to answer user queries with structured, cited JSON outputs.

## Project Structure
Once fully implemented, the directory structure will be organized as follows:
```
E:/applab-test/
├── applab-test-content1       # Original assessment requirements
├── architecture/             # Section A deliverables
│   └── design.md             # Multitenant RAG + Agents design document
├── src/                      # Section B source code
│   ├── __init__.py
│   ├── agent.py              # Main Agent Planner and Core Loop
│   ├── registry.py           # Tool registry and schemas
│   ├── tools/                # Live tools implementations
│   │   ├── __init__.py
│   │   ├── web_search.py     # DuckDuckGo integration
│   │   └── weather.py        # Weather dummy tool
│   ├── models.py             # Pydantic schemas for inputs and structured outputs
│   └── main.py               # Fast API or simple runner entrypoint
├── tests/                    # Test suite
│   ├── __init__.py
│   ├── test_agent.py         # Agent loop & planning tests
│   └── test_tools.py         # Web search & weather tool tests
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment variables
└── README.md                 # Setup, usage guide, and assessment explanations
```

## Build and Run Commands

### Development Setup
Create a virtual environment and install dependencies:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Running the QA Service
Execute the agent runner directly or start the service:
```bash
# Run CLI tool
python -m src.main --query "What is the weather in Tokyo?"

# Run the API server (if implemented as a FastAPI app)
uvicorn src.main:app --reload
```

### Running Tests
Execute unit and integration tests:
```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_agent.py

# Run with stdout output enabled
pytest -s
```

### Linting and Formatting
Check code style, syntax, and formatting:
```bash
# Lint code using Ruff
ruff check src/

# Format code using Ruff
ruff format src/
```

## Coding Guidelines

### Architecture & Design Rules
- **Planner / Core Loop**: Implement a transparent, custom Agent Planner and Tool Registry without relying on complex framework abstractions (like LangChain) to show full control over the agent loop.
- **Structured I/O**: Ensure all inputs and outputs conform strictly to Pydantic JSON schemas. The final output must match the specified schema containing `answer`, `sources`, `latency_ms` (broken down by step), and `tokens`.
- **Parallelism & Concurrency**: Utilize `httpx.AsyncClient` or `asyncio` to run independent tool calls in parallel to minimize latency.
- **Robustness**: Implement retry logic and timeouts for all external HTTP calls.
- **Network Policy Layer**: Enforce a basic policy check on search results/sources to filter or block disallowed domains if required.
