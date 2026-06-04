from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Source(BaseModel):
    name: str = Field(description="Name of the source/website")
    url: str = Field(description="URL of the source")

class LatencyMS(BaseModel):
    total: float = Field(description="Total latency in milliseconds")
    by_step: Dict[str, float] = Field(
        description="Detailed latency breakdown by step (e.g. 'planner', 'tool_execution', 'generation')"
    )

class TokenUsage(BaseModel):
    prompt: int = Field(default=0, description="Tokens used in prompt")
    completion: int = Field(default=0, description="Tokens used in completion")

class AgentOutput(BaseModel):
    answer: str = Field(description="Grounded, cited answer explaining tool findings")
    sources: List[Source] = Field(default_factory=list, description="Sources/citations backing the answer")
    latency_ms: LatencyMS = Field(description="Detailed step-by-step latency metrics")
    tokens: TokenUsage = Field(description="LLM token usage metrics")
