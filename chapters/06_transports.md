# Chapter 6 — Transports

## The Three Transports

| Transport | Use Case | How it Works |
|---|---|---|
| **stdio** | Local processes | Client spawns server as subprocess, uses stdin/stdout |
| **SSE** | Remote servers, web | Client subscribes to `/sse`, sends requests via POST |
| **HTTP Streamable** | Modern remote servers | Single endpoint, bidirectional HTTP streaming |

The MCP messages are identical regardless of transport. Only the delivery mechanism changes.

## stdio (Default)

Your server process receives JSON-RPC on stdin and writes responses to stdout. Claude Desktop uses this for local servers.

**Critical rule:** Never `print()` to stdout in a stdio server. It corrupts the protocol. Use `sys.stderr` for debug output.

```python
# chapter06/stdio_server.py
from fastmcp import FastMCP
import sys

mcp = FastMCP("stdio-demo")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    print("debug output goes here", file=sys.stderr)  # CORRECT
    # print("this breaks everything")                  # WRONG
    return f"pong: {message} via stdio"

if __name__ == "__main__":
    mcp.run()  # default transport is stdio
```

## SSE Transport

```python
# chapter06/sse_server.py
from fastmcp import FastMCP

mcp = FastMCP("sse-demo")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    return f"pong: {message} via SSE"

@mcp.resource("status://health")
def health() -> str:
    """Server health status."""
    return '{"status": "ok", "transport": "sse"}'

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8080)
```

Run it:
```bash
python chapter06/sse_server.py
# Server running at http://0.0.0.0:8080
```

Add to Claude Desktop config:
```json
{
  "mcpServers": {
    "remote-demo": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

## HTTP Streamable Transport

The newer transport — single endpoint instead of two:

```python
# chapter06/http_streamable_server.py
from fastmcp import FastMCP

mcp = FastMCP("http-demo")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    return f"pong: {message} via HTTP Streamable"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8081)
```

## Multi-Transport Launcher

One server, any transport, controlled by CLI argument:

```python
# chapter06/launcher.py
import argparse
from fastmcp import FastMCP

mcp = FastMCP("multi-transport")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    return f"pong: {message}"

@mcp.resource("info://transport")
def transport_info() -> str:
    """Information about this server."""
    return '{"server": "multi-transport", "version": "1.0"}'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)
```

Usage:
```bash
python launcher.py                          # stdio
python launcher.py --transport sse          # SSE on :8080
python launcher.py --transport http --port 9000  # HTTP on :9000
```

---

## Project 6: Same Server, Three Transports

Build a weather-like server and verify it works over all three transports. Confirm the behavior is identical regardless of transport.

```python
# chapter06/weather_server.py
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
```

**Tests to run:**
1. stdio via Claude Desktop — ask about weather in London
2. SSE — add to config as `{"url": "http://localhost:8080/sse"}`, ask same question
3. HTTP Streamable — `--transport http --port 8081`, same question

Confirm identical responses across all three.
