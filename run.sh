#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Building Docker Image: agentic-qa-service ==="
docker build -t agentic-qa-service .

echo ""
echo "=== Starting Agentic QA Service Container ==="
echo "Access the API Server at http://localhost:8000"
echo "Healthcheck endpoint: http://localhost:8000/health"
echo "Press Ctrl+C to stop the server"
echo ""

# Run the container, mapping port 8000, passing the ANTHROPIC_API_KEY if available locally
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "WARNING: ANTHROPIC_API_KEY environment variable is not set locally."
  echo "You must provide it inside the container or pass it at runtime."
  docker run -p 8000:8000 agentic-qa-service
else
  docker run -p 8000:8000 -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" agentic-qa-service
fi
