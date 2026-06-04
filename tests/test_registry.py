import pytest
from pydantic import BaseModel, Field
from typing import Dict, Any
from src.registry import Tool, ToolRegistry, ValidationError

# Define a dummy input schema for testing
class AddNumbersInput(BaseModel):
    a: int = Field(description="First number to add")
    b: int = Field(description="Second number to add")

# Define a dummy tool
async def add_numbers(a: int, b: int) -> Dict[str, Any]:
    return {"result": a + b}

def test_tool_creation():
    """Test that a Tool object can be created with schema and metadata."""
    tool = Tool(
        name="add_numbers",
        description="Adds two integers together",
        input_schema=AddNumbersInput,
        func=add_numbers
    )
    assert tool.name == "add_numbers"
    assert "adds two integers" in tool.description.lower()

    # Verify JSON Schema output for the Gemini
    schema = tool.get_json_schema()
    assert schema["name"] == "add_numbers"
    assert "properties" in schema["parameters"]
    assert "a" in schema["parameters"]["properties"]
    assert "b" in schema["parameters"]["properties"]

@pytest.mark.asyncio
async def test_registry_registration_and_execution():
    """Test registering a tool and executing it through the registry."""
    registry = ToolRegistry()

    # Register the tool
    registry.register(
        name="add_numbers",
        description="Adds two integers together",
        input_schema=AddNumbersInput,
        func=add_numbers
    )

    # Verify the registry lists it
    schemas = registry.get_gemini_tools()
    assert len(schemas) == 1
    assert schemas[0]["name"] == "add_numbers"

    # Execute the tool
    result = await registry.execute("add_numbers", {"a": 10, "b": 20})
    assert result["result"] == 30

    # Verify that a non-existent tool raises KeyError
    with pytest.raises(KeyError):
        await registry.execute("non_existent", {})

def test_registry_invalid_arguments():
    """Test that invalid arguments trigger a ValidationError."""
    registry = ToolRegistry()
    registry.register(
        name="add_numbers",
        description="Adds two integers",
        input_schema=AddNumbersInput,
        func=add_numbers
    )

    # Test that the registry raises ValidationError for invalid input
    # We'll check that the Tool.execute method raises ValidationError
    # by trying to execute with non-integer arguments
    # Note: We need to access the tool directly to test this
    tool = registry.tools["add_numbers"]

    # Test that executing with invalid args raises ValidationError
    # We'll test this by checking the tool directly
    import asyncio
    try:
        # This should raise ValidationError because "not_a_number" is not an int
        result = asyncio.run(tool.execute({"a": "not_a_number", "b": 20}))
    except ValidationError:
        # Expected
        pass
    else:
        assert False, "Expected ValidationError for invalid input"

@pytest.mark.asyncio
async def test_registry_tool_not_found():
    """Test that executing a non-registered tool raises KeyError."""
    registry = ToolRegistry()
    with pytest.raises(KeyError):
        await registry.execute("ghost_tool", {"a": 1})
