"""
Simulated weather server — same tools work over stdio, SSE, and HTTP.
"""
from fastmcp import FastMCP
import random, json
from datetime import datetime

mcp = FastMCP("weather")

# Simulated weather data
CITIES = {
    "london": {"country": "UK", "lat": 51.5, "lon": -0.1},
    "new york": {"country": "US", "lat": 40.7, "lon": -74.0},
    "tokyo": {"country": "JP", "lat": 35.7, "lon": 139.7},
    "sydney": {"country": "AU", "lat": -33.9, "lon": 151.2},
    "paris": {"country": "FR", "lat": 48.9, "lon": 2.3},
}

def fake_weather(city: str) -> dict:
    seed = sum(ord(c) for c in city) + datetime.now().hour
    random.seed(seed)
    conditions = ["Sunny", "Cloudy", "Rainy", "Partly Cloudy", "Foggy", "Windy"]
    return {
        "city": city.title(),
        "temperature_c": round(random.uniform(-5, 35), 1),
        "humidity_percent": random.randint(30, 95),
        "condition": random.choice(conditions),
        "wind_kph": random.randint(0, 60),
        "fetched_at": datetime.now().isoformat(),
    }

@mcp.tool()
def get_weather(city: str) -> str:
    """Get current weather for a city. Returns temperature, humidity, and conditions."""
    city_lower = city.lower()
    meta = CITIES.get(city_lower, {"country": "Unknown", "lat": 0.0, "lon": 0.0})
    weather = fake_weather(city_lower)
    weather.update(meta)
    return json.dumps(weather, indent=2)

@mcp.tool()
def compare_weather(city1: str, city2: str) -> str:
    """Compare weather between two cities side by side."""
    w1 = fake_weather(city1.lower())
    w2 = fake_weather(city2.lower())
    return f"""{city1.title()}: {w1['temperature_c']}°C, {w1['condition']}, {w1['humidity_percent']}% humidity
{city2.title()}: {w2['temperature_c']}°C, {w2['condition']}, {w2['humidity_percent']}% humidity
Warmer: {city1.title() if w1['temperature_c'] > w2['temperature_c'] else city2.title()}"""

@mcp.tool()
def list_available_cities() -> str:
    """List all cities with weather data available."""
    return ", ".join(c.title() for c in CITIES.keys())

@mcp.resource("weather://cities")
def cities_resource() -> str:
    """All available cities with coordinates."""
    return json.dumps(CITIES, indent=2)

@mcp.resource("weather://current/{city}")
def current_weather_resource(city: str) -> str:
    """Current weather for a city as a resource."""
    return json.dumps(fake_weather(city.lower()), indent=2)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio")
    p.add_argument("--port", type=int, default=8080)
    args = p.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, port=args.port)