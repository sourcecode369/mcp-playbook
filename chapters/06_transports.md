# Chapter 6 — Transports

## What is a Transport?

A transport is the mechanism by which JSON-RPC messages travel between the client and the server. The MCP protocol defines what messages look like — transports define how they move.

This separation is fundamental: **your server code doesn't change based on transport**. The same tools, resources, and prompts you define with FastMCP work identically over stdio, SSE, or HTTP. The only thing that changes is `mcp.run(transport=...)`.

## The Three Transports

| Transport | Use Case | Direction | When to Use |
|---|---|---|---|
| **stdio** | Local processes | Bidirectional via stdin/stdout | Claude Desktop, CLI tools, local dev |
| **SSE** | Remote servers | Client POSTs requests, server pushes via SSE stream | Browser clients, remote hosting |
| **HTTP Streamable** | Modern remote servers | Single endpoint, bidirectional HTTP | New deployments, production servers |

## Why Three Transports Exist

**stdio** came first. It's the simplest: two pipes, zero network. Works perfectly for local tools.

**SSE** was added to allow remote servers. Server-Sent Events is a web standard for server-push — the client opens a long-lived GET connection and the server pushes data down it. The client sends requests via normal HTTP POSTs to a separate endpoint.

**HTTP Streamable** is the newer standard. It consolidates SSE's two endpoints into one, uses proper HTTP streaming in both directions, and is what new remote servers should default to.

## How stdio Works (Deep Dive)

```
Claude Desktop
    │  spawns process: python server.py
    │
    ├── writes JSON to server's stdin  ──► your server reads it
    │                                        your server processes it
    └── reads JSON from server's stdout ◄── your server writes response
```

Claude Desktop treats your server like any other subprocess. stdin and stdout are the communication channel. This is why:
- `print()` in your server breaks everything — it writes to stdout, which the client reads as JSON and fails to parse
- You must use `sys.stderr` for any debug output
- The server stays alive as a process as long as Claude Desktop is running

## How SSE Works (Deep Dive)

```
Client                              Server
  │── GET /sse ──────────────────►  │  (open long-lived connection)
  │◄── data: {...} ─────────────────│  (server pushes responses here)
  │── POST /messages ─────────────► │  (client sends requests here)
  │◄── 202 Accepted ────────────────│
```

Two separate HTTP connections running simultaneously:
1. A long-lived GET that stays open — server pushes responses down it
2. Short-lived POSTs for each request — client sends a message, gets 202 back

The actual response to a POST arrives asynchronously via the SSE stream, matched by request ID.

## How HTTP Streamable Works (Deep Dive)

```
Client                              Server
  │── POST /mcp ──────────────────► │
  │◄── streaming response ──────────│  (server streams back responses)
```

One endpoint. The client POSTs a request, the server streams the response back. Cleaner than SSE but requires HTTP/1.1 chunked transfer or HTTP/2.

## stdio (Default)

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

---

## When to Use Which Transport

**Use stdio when:**
- Running locally on the same machine as the client
- Using Claude Desktop
- Building CLI tools or scripts
- During development and testing

**Use SSE when:**
- Deploying to a remote server
- Supporting browser-based clients
- Your infrastructure is already HTTP-based
- You need backwards compatibility with older MCP clients

**Use HTTP Streamable when:**
- Building new remote deployments from scratch
- You want the cleanest, most modern MCP setup
- Your infrastructure supports HTTP/2

**Rule of thumb:**
- Local = stdio
- Remote (new) = HTTP Streamable
- Remote (legacy/compatibility) = SSE

---

## Common Mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| `print()` in stdio server | JSON parse error in client | Use `sys.stderr` |
| Wrong port in config | Server not connecting | Match `--port` to config URL |
| Running SSE server but using stdio config | Connection refused | Use `"url":` key not `"command":` in config |
| Firewall blocking port | SSE/HTTP not reachable | Open port or use localhost |
| Server not running when Claude Desktop connects | Failed status | Start server before restarting Desktop |
