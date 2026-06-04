from typing import Callable, Any, Dict, List, Type
from pydantic import BaseModel, ValidationError as PydanticValidationError

class ValidationError(Exception):
    """Raised when tool inputs fail schema validation."""
    pass

class Tool:
    """Represents a tool that can be executed by the agent."""
    def __init__(
        self,
        name: str,
        description: str,
        input_schema: Type[BaseModel],
        func: Callable[..., Any]
    ):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.func = func

    def get_json_schema(self) -> Dict[str, Any]:
        """Returns the JSON schema of the tool for LLM ingestion."""
        # Convert Pydantic model to JSON schema format
        pydantic_schema = self.input_schema.model_json_schema()

        # For Gemini SDK compatibility, we return in the structure
        # that Gemini's tools expect (FunctionDeclaration).
        return {
            "name": self.name,
            "description": self.description,
            "parameters": pydantic_schema
        }

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Validates arguments against the schema and executes the tool function."""
        try:
            # Validate input using Pydantic
            validated_input = self.input_schema(**arguments)
        except PydanticValidationError as e:
            # Convert to our custom ValidationError so the agent can catch it cleanly
            raise ValidationError(f"Invalid inputs for tool '{self.name}': {str(e)}")

        # Execute the function (async)
        result = self.func(**validated_input.model_dump())
        import inspect
        if inspect.iscoroutine(result):
            return await result
        return result


class ToolRegistry:
    """Registry to manage and execute tools."""
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(
        self,
        name: str,
        description: str,
        input_schema: Type[BaseModel],
        func: Callable[..., Any]
    ) -> None:
        """Registers a new tool in the registry."""
        self.tools[name] = Tool(
            name=name,
            description=description,
            input_schema=input_schema,
            func=func
        )

    def get_gemini_tools(self) -> List[Dict[str, Any]]:
        """Returns tool declarations formatted for Google Gemini."""
        return [tool.get_json_schema() for tool in self.tools.values()]

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """Executes a registered tool by name with the given arguments."""
        if name not in self.tools:
            raise KeyError(f"Tool '{name}' not found in registry.")

        return await self.tools[name].execute(arguments)
