# Chapter 2 — FastMCP Introduction

## FastMCP vs Raw MCP SDK

| | Raw `mcp` SDK | FastMCP |
|---|---|---|
| Server creation | `app = Server("name")` | `mcp = FastMCP("name")` |
| Register tool | `@app.list_tools()` + `@app.call_tool()` | `@mcp.tool()` |
| Schema | Write JSON Schema manually | Generated from type hints + docstring |
| Boilerplate | ~30 lines per tool | ~5 lines per tool |
| Underlying protocol | Direct | Same — FastMCP wraps the raw SDK |

FastMCP is to MCP what FastAPI is to Starlette. Same protocol, far less boilerplate.

## Your First FastMCP Server

```python
# chapter02/first_server.py
from fastmcp import FastMCP

mcp = FastMCP("my-first-server")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

@mcp.tool()
def greet(name: str, formal: bool = False) -> str:
    """Greet a person. Set formal=True for a professional greeting."""
    if formal:
        return f"Good day, {name}."
    return f"Hey {name}!"

if __name__ == "__main__":
    mcp.run()
```

That's it. FastMCP:
- Generates the tool schema from type hints (`int`, `str`, `bool`)
- Uses the docstring as the tool description
- Handles `list_tools`, `call_tool`, `initialize` — all automatically

## How FastMCP Generates Schemas

```python
@mcp.tool()
def search(
    query: str,
    max_results: int = 10,
    include_images: bool = False
) -> list[dict]:
    """
    Search for information on the web.

    Args:
        query: The search query string
        max_results: Maximum number of results to return (1-50)
        include_images: Whether to include image results
    """
    ...
```

FastMCP generates:
```json
{
  "name": "search",
  "description": "Search for information on the web.\n\nArgs:\n    query: ...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"},
      "max_results": {"type": "integer", "default": 10},
      "include_images": {"type": "boolean", "default": false}
    },
    "required": ["query"]
  }
}
```

Parameters with defaults are not required. Parameters without defaults are required.

## Test with Claude Desktop

Add to config:
```json
{
  "mcpServers": {
    "first-server": {
      "command": "python",
      "args": ["/absolute/path/to/chapter02/first_server.py"]
    }
  }
}
```

Restart Claude Desktop. Ask: *"Add 1337 and 42"* — Claude will call `add`.

## Test with Claude API

```python
# chapter02/test_with_api.py
from anthropic import Anthropic
from dotenv import load_dotenv
import subprocess, json, asyncio

load_dotenv()

# Option A: Mirror the tools manually in the API call
client = Anthropic()

tools = [
    {
        "name": "add",
        "description": "Add two numbers together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "greet",
        "description": "Greet a person. Set formal=True for a professional greeting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "formal": {"type": "boolean", "default": False}
            },
            "required": ["name"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    """Execute a tool call by calling the actual function."""
    if name == "add":
        return str(args["a"] + args["b"])
    elif name == "greet":
        n, formal = args["name"], args.get("formal", False)
        return f"Good day, {n}." if formal else f"Hey {n}!"
    return f"Unknown tool: {name}"

def chat_with_tools(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=512,
            tools=tools,
            messages=messages
        )

        # If Claude wants to use a tool
        if response.stop_reason == "tool_use":
            # Add Claude's response to messages
            messages.append({"role": "assistant", "content": response.content})

            # Process all tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool called: {block.name}({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            # Add tool results and continue
            messages.append({"role": "user", "content": tool_results})

        else:
            # Claude is done, return final text
            return response.content[0].text

# Test it
print(chat_with_tools("Add 1337 and 42"))
print(chat_with_tools("Greet Alice formally"))
print(chat_with_tools("What is 15 times 8? Then greet the answer as a name."))
```

## Project 2A: Five-Tool Utility Server

Build a server with 5 unrelated but useful tools:

```python
# chapter02/utility_server.py
from fastmcp import FastMCP
import math, hashlib, base64, re
from datetime import datetime

mcp = FastMCP("utilities")

@mcp.tool()
def calculate(expression: str) -> str:
    """
    Evaluate a safe mathematical expression.
    Supports: +, -, *, /, **, sqrt, log, sin, cos, pi, e
    Example: "sqrt(144) + 2**8"
    """
    allowed = {
        k: getattr(math, k) for k in dir(math) if not k.startswith("_")
    }
    allowed.update({"abs": abs, "round": round})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)
    except Exception as e:
        return f"Error: {e}"

@mcp.tool()
def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
    Hash a string using md5, sha1, sha256, or sha512.
    Returns the hex digest.
    """
    if algorithm not in ("md5", "sha1", "sha256", "sha512"):
        return f"Unsupported algorithm: {algorithm}"
    h = hashlib.new(algorithm)
    h.update(text.encode())
    return h.hexdigest()

@mcp.tool()
def encode_decode(text: str, operation: str = "encode") -> str:
    """
    Base64 encode or decode a string.
    operation must be 'encode' or 'decode'.
    """
    if operation == "encode":
        return base64.b64encode(text.encode()).decode()
    elif operation == "decode":
        try:
            return base64.b64decode(text.encode()).decode()
        except Exception as e:
            return f"Decode error: {e}"
    return f"Unknown operation: {operation}"

@mcp.tool()
def count_words(text: str) -> dict:
    """
    Count words, characters, sentences, and unique words in text.
    Returns a dict with counts.
    """
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    return {
        "words": len(words),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "sentences": len(sentences),
        "unique_words": len(set(w.lower().strip(".,!?") for w in words))
    }

@mcp.tool()
def timestamp(
    format: str = "iso",
    timezone: str = "utc"
) -> str:
    """
    Get the current timestamp.
    format options: iso, unix, human, date, time
    timezone: utc or local
    """
    from datetime import timezone as tz
    now_utc = datetime.now(tz.utc)
    now = now_utc if timezone == "utc" else datetime.now()

    formats = {
        "iso": now.isoformat(),
        "unix": str(int(now.timestamp())),
        "human": now.strftime("%B %d, %Y at %I:%M %p"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
    }
    return formats.get(format, now.isoformat())

if __name__ == "__main__":
    mcp.run()
```

Test in Claude Desktop: *"Hash my email address with SHA256"* or *"What's the current unix timestamp?"*

Test via API — add all 5 tools to a `tools` list and verify Claude picks the right one for each query across 10 test prompts.
