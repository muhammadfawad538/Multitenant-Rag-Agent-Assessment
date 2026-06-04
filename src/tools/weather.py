from pydantic import BaseModel, Field
from typing import Literal, Dict, Any
import random

class WeatherInput(BaseModel):
    location: str = Field(description="The city and state/country to get the weather for (e.g., 'Tokyo', 'San Francisco, CA')")
    unit: Literal["celsius", "fahrenheit"] = Field(default="celsius", description="The temperature unit to return")

async def get_weather(location: str, unit: str = "celsius") -> Dict[str, Any]:
    """A dummy tool that returns realistic weather data for any location."""
    # Seed deterministic or semi-random weather based on the name length to simulate API
    loc_hash = sum(ord(c) for c in location)

    # Generate realistic values
    temp_c = 15 + (loc_hash % 20)  # Between 15 and 35
    humidity = 40 + (loc_hash % 50)  # Between 40% and 90%

    conditions = ["Sunny", "Partly Cloudy", "Rainy", "Overcast", "Windy"]
    condition = conditions[loc_hash % len(conditions)]

    temp = temp_c if unit == "celsius" else int(temp_c * 9/5 + 32)

    return {
        "location": location,
        "temperature": temp,
        "unit": unit,
        "condition": condition,
        "humidity": f"{humidity}%",
        "forecast": f"Expect {condition.lower()} conditions in {location} today with a humidity of {humidity}%."
    }
