# Chapter 15 — MCP Inspector & Debugging

## MCP Inspector

The official debugging tool — gives you a visual web UI to browse tools, resources, prompts, and inspect raw messages.

```bash
# Install and run against any server
npx @modelcontextprotocol/inspector python chapter02/utility_server.py

# Opens at http://localhost:5173
```

What you can do in the Inspector:
- **Tools tab**: list all tools, see schemas, click to test with real inputs
- **Resources tab**: list and read any resource by URI
- **Prompts tab**: list prompts and generate them with arguments
- **History**: every raw JSON-RPC message logged in real time

This is your first debugging stop for any server issue.

---

## Common Errors and Fixes

| Symptom | Cause | Fix |
|---|---|---|
| Server not in Claude Desktop | Wrong absolute path | Use `which python` to get full Python path |
| Tools not appearing | `list_tools` raises exception | Check stderr logs |
| `print()` causes JSON errors | stdout pollution | Use `sys.stderr` for all debug output |
| Tool call hangs | Blocking code in async handler | Wrap with `asyncio.to_thread()` |
| JSON decode error | Non-JSON to stdout | Remove all `print()` statements |
| `initialize` timeout | Server crashed on startup | Run server directly: `python server.py` |
| Sampling not working | Client doesn't support it | Use Claude Desktop, not a basic client |

---

## Debugging Techniques

### 1. Run the server standalone to see errors

```bash
# Run server directly before connecting via MCP
python chapter09/github_server.py

# If it crashes, you'll see the traceback directly
# instead of a cryptic "server failed to connect" message
```

### 2. stderr logging in FastMCP

FastMCP logs to stderr automatically. Capture it:

```python
# chapter15/debug_server.py
from fastmcp import FastMCP
import sys, logging

# Enable verbose logging to stderr
logging.basicConfig(stream=sys.stderr, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

mcp = FastMCP("debug-demo")

@mcp.tool()
def sometimes_fails(value: int) -> str:
    """Tool that sometimes raises an exception."""
    logging.debug(f"Tool called with value={value}")
    if value < 0:
        logging.error(f"Negative value received: {value}")
        raise ValueError(f"Value must be non-negative, got {value}")
    return str(value * 2)

if __name__ == "__main__":
    logging.info("Server starting...")
    mcp.run()
```

Capture stderr in Claude Desktop config:
```json
{
  "mcpServers": {
    "debug-demo": {
      "command": "python",
      "args": ["/path/to/debug_server.py"],
      "stderr": "/tmp/mcp-debug.log"
    }
  }
}
```

Then: `tail -f /tmp/mcp-debug.log`

### 3. Wrap blocking code correctly

```python
from fastmcp import FastMCP
import asyncio

mcp = FastMCP("blocking-demo")

def slow_blocking_function(data: str) -> str:
    """This function blocks the event loop if called directly."""
    import time
    time.sleep(2)  # simulates slow IO
    return data.upper()

@mcp.tool()
async def process_data(data: str) -> str:
    """Process data without blocking the event loop."""
    # WRONG:
    # result = slow_blocking_function(data)

    # CORRECT: runs in thread pool
    result = await asyncio.to_thread(slow_blocking_function, data)
    return result

if __name__ == "__main__":
    mcp.run()
```

### 4. Wire spy for raw message inspection

```bash
# From chapter01 — use the wire_spy.py to log all messages
python chapter01/wire_spy.py python chapter09/github_server.py

# Then connect Claude Desktop to the spy instead of directly
# All messages logged to /tmp/mcp_wire.log
tail -f /tmp/mcp_wire.log
```

---

## Project 15: Diagnose a Broken Server

Here is a server with 5 intentional bugs. Find and fix each one:

```python
# chapter15/broken_server.py — DO NOT RUN without reading the bugs first

from fastmcp import FastMCP
import json

mcp = FastMCP("broken")

# BUG 1: print() to stdout will corrupt protocol
@mcp.tool()
def greet(name: str) -> str:
    """Greet a user."""
    print(f"Greeting {name}")  # BUG: should be sys.stderr or ctx.info
    return f"Hello, {name}!"

# BUG 2: blocking sleep in async context
@mcp.tool()
async def slow_tool(seconds: int) -> str:
    """Wait for some seconds."""
    import time
    time.sleep(seconds)  # BUG: blocks event loop, use asyncio.sleep
    return "Done"

# BUG 3: no input validation — path traversal possible
@mcp.tool()
def read_file(path: str) -> str:
    """Read any file."""
    return open(path).read()  # BUG: no path validation or sandboxing

# BUG 4: swallowed exception hides the real error
@mcp.tool()
def parse_data(data: str) -> str:
    """Parse JSON data."""
    try:
        return str(json.loads(data))
    except:
        return ""  # BUG: hides error, LLM can't know what went wrong

# BUG 5: returns None instead of string
@mcp.tool()
def maybe_return(value: int) -> str:
    """Return double the value if positive."""
    if value > 0:
        return str(value * 2)
    # BUG: returns None when value <= 0, should return an error message

if __name__ == "__main__":
    mcp.run()
```

**Task:** Fix all 5 bugs and write a test for each one.
