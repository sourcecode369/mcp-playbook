# Chapter 1 — Protocol Foundations

> Read this before using FastMCP. Understanding what's underneath makes everything else click.

## What is MCP?

MCP standardizes how AI models talk to external tools and data. Before MCP, every app wrote custom integrations per tool. MCP says: one protocol, any tool, any model.

## The Three Actors

```
┌─────────────────────────────────────────────────────┐
│  HOST  (Claude Desktop, your Python app)            │
│  ┌────────────┐        ┌────────────┐               │
│  │ MCP Client │        │ MCP Client │  one per server│
│  └─────┬──────┘        └─────┬──────┘               │
└────────┼──────────────────────┼─────────────────────┘
         │ stdio / SSE           │ stdio / SSE
         ▼                       ▼
  ┌────────────┐          ┌────────────┐
  │ MCP Server │          │ MCP Server │
  │ (notes)    │          │ (github)   │
  └────────────┘          └────────────┘
```

- **Host**: the app embedding the LLM
- **Client**: lives inside the host, one per server connection
- **Server**: exposes tools, resources, prompts

## JSON-RPC 2.0 — The Wire Format

Every MCP message is JSON-RPC 2.0. Three types only:

```json
// Request — expects a response
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": { "name": "add", "arguments": {"a": 1, "b": 2} }
}

// Response
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": { "content": [{ "type": "text", "text": "3" }] }
}

// Notification — no response expected
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

## Session Lifecycle

```
Client                          Server
  │──── initialize ────────────►│   (declare protocol version + capabilities)
  │◄─── InitializeResult ───────│   (server declares its capabilities)
  │──── notifications/initialized►│  (handshake complete)
  │                              │
  │──── tools/list ─────────────►│
  │◄─── {tools: [...]} ─────────│
  │──── tools/call ─────────────►│
  │◄─── {content: [...]} ───────│
```

The `initialize` handshake is where protocol version and capabilities are negotiated. If you skip it, nothing works.

## Capabilities

During `initialize`, both sides declare what they support:

```json
// Client capabilities
{
  "roots": { "listChanged": true },
  "sampling": {}
}

// Server capabilities
{
  "tools": { "listChanged": true },
  "resources": { "subscribe": true, "listChanged": true },
  "prompts": { "listChanged": true },
  "logging": {}
}
```

A server that declares `tools.listChanged` can send `notifications/tools/list_changed` to tell the client its tool list changed dynamically.

---

## Hands-On: Protocol Explorer

Inspect raw MCP messages without any framework:

```python
# chapter01/protocol_explorer.py
import asyncio, json, subprocess

async def explore():
    proc = await asyncio.create_subprocess_exec(
        "python", "-c", """
from fastmcp import FastMCP
mcp = FastMCP("demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

mcp.run()
""",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def send(msg):
        raw = json.dumps(msg) + "\n"
        print(f"\n>>> {json.dumps(msg, indent=2)}")
        proc.stdin.write(raw.encode())
        await proc.stdin.drain()

    async def recv():
        line = await proc.stdout.readline()
        msg = json.loads(line)
        print(f"\n<<< {json.dumps(msg, indent=2)}")
        return msg

    # Step 1: initialize handshake
    await send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}},
            "clientInfo": {"name": "explorer", "version": "0.1.0"}
        }
    })
    await recv()

    # Step 2: initialized notification
    await send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # Step 3: list tools
    await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    await recv()

    # Step 4: call a tool
    await send({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 10, "b": 32}}
    })
    await recv()

    proc.terminate()
    print("\n\nDone — you just spoke raw MCP protocol.")

asyncio.run(explore())
```

Run it and study every message. This is what FastMCP generates for you automatically.

---

## Hands-On: Wire Spy

Log all messages flowing between Claude Desktop and your server:

```python
# chapter01/wire_spy.py
"""
Transparent proxy that logs all MCP messages to a file.
Use as a wrapper in Claude Desktop config instead of your server directly.
"""
import sys, json, threading, os

LOG = open("/tmp/mcp_wire.log", "w")
TARGET = sys.argv[1:]  # e.g. ["python", "my_server.py"]

import subprocess
proc = subprocess.Popen(
    TARGET,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

def pipe_with_log(src, dst, label):
    while True:
        line = src.readline()
        if not line: break
        try:
            msg = json.loads(line)
            LOG.write(f"[{label}] {json.dumps(msg)}\n")
            LOG.flush()
        except Exception:
            pass
        dst.write(line)
        dst.flush()

t1 = threading.Thread(target=pipe_with_log, args=(sys.stdin.buffer, proc.stdin, "IN "), daemon=True)
t2 = threading.Thread(target=pipe_with_log, args=(proc.stdout, sys.stdout.buffer, "OUT"), daemon=True)
t1.start(); t2.start()
proc.wait()
```

Claude Desktop config:
```json
{
  "mcpServers": {
    "my-server-spied": {
      "command": "python",
      "args": ["/path/to/wire_spy.py", "python", "/path/to/server.py"]
    }
  }
}
```

Watch `/tmp/mcp_wire.log` while using Claude Desktop. Every JSON-RPC message will appear.

---

## Key Takeaways

- MCP is just JSON-RPC 2.0 over stdin/stdout (or HTTP)
- Every interaction starts with `initialize` → `notifications/initialized`
- Tools, resources, and prompts are all just methods on top of this foundation
- FastMCP handles all of this for you — but now you know what it's doing
