# Chapter 3 — Tools

## Tool Design Principles

**1. Description is everything**
The LLM reads your description to decide when to call the tool. Be specific.

Bad: `"Get data"`
Good: `"Fetch current weather conditions for a city. Use when user asks about weather, temperature, or forecast."`

**2. Type hints generate schemas**
```python
@mcp.tool()
def my_tool(
    required_str: str,           # required, string
    required_int: int,           # required, integer
    optional_float: float = 1.0, # optional, has default
    flag: bool = False,          # optional boolean
) -> str:
    ...
```

**3. Use enums for constrained choices**
```python
from typing import Literal

@mcp.tool()
def resize_image(
    path: str,
    size: Literal["small", "medium", "large", "original"] = "medium"
) -> str:
    """Resize an image to a preset size."""
    ...
```

**4. Return structured data as strings or dicts**
```python
# Return plain text
return "Operation succeeded"

# Return structured data (FastMCP serializes it)
return {"status": "ok", "count": 42, "items": [...]}

# Return error (keep conversation going)
return f"Error: file not found at {path}"
```

**5. Raise for unrecoverable errors**
```python
@mcp.tool()
def read_file(path: str) -> str:
    """Read a file."""
    if not os.path.exists(path):
        return f"File not found: {path}"  # soft error — LLM can react
    if os.path.getsize(path) > 10_000_000:
        raise ValueError("File too large (>10MB)")  # hard stop
    return open(path).read()
```

---

## Hands-On: Error Handling Patterns

```python
# chapter03/error_handling.py
from fastmcp import FastMCP
import httpx, json
from typing import Literal

mcp = FastMCP("error-patterns")

@mcp.tool()
def safe_divide(a: float, b: float) -> str:
    """
    Divide a by b. Returns an error message if b is zero
    instead of crashing, so the LLM can recover gracefully.
    """
    if b == 0:
        return "Cannot divide by zero. Please provide a non-zero divisor."
    return str(a / b)

@mcp.tool()
def fetch_url(url: str) -> str:
    """
    Fetch the content of a URL. Returns an error with details
    if the request fails, so the LLM knows what went wrong.
    """
    if not url.startswith(("http://", "https://")):
        return f"Invalid URL: must start with http:// or https://"
    try:
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        resp.raise_for_status()
        # Truncate large responses
        text = resp.text[:5000]
        if len(resp.text) > 5000:
            text += f"\n\n[Truncated — {len(resp.text)} total chars]"
        return text
    except httpx.TimeoutException:
        return f"Request timed out after 10 seconds: {url}"
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code} error for {url}"
    except Exception as e:
        return f"Request failed: {type(e).__name__}: {e}"

@mcp.tool()
def parse_json(text: str) -> str:
    """
    Parse and pretty-print a JSON string.
    Returns a helpful error message if the JSON is invalid.
    """
    try:
        parsed = json.loads(text)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError as e:
        return f"Invalid JSON at position {e.pos}: {e.msg}\nInput was: {text[:200]}"

if __name__ == "__main__":
    mcp.run()
```

---

## Hands-On: Async Tools

Use `async def` for tools that call external services — it keeps the server responsive:

```python
# chapter03/async_tools.py
from fastmcp import FastMCP
import asyncio, httpx
from typing import Literal

mcp = FastMCP("async-demo")

@mcp.tool()
async def fetch_multiple_urls(urls: list[str]) -> str:
    """
    Fetch multiple URLs concurrently and return a summary.
    Much faster than fetching them one by one.
    """
    async def fetch_one(url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, follow_redirects=True)
                return {
                    "url": url,
                    "status": resp.status_code,
                    "size": len(resp.text),
                    "ok": resp.status_code < 400
                }
        except Exception as e:
            return {"url": url, "error": str(e), "ok": False}

    results = await asyncio.gather(*[fetch_one(u) for u in urls[:10]])
    lines = []
    for r in results:
        if r.get("ok"):
            lines.append(f"✓ {r['url']} — {r['status']} ({r['size']} chars)")
        else:
            lines.append(f"✗ {r['url']} — {r.get('error', r.get('status'))}")
    return "\n".join(lines)

@mcp.tool()
async def run_concurrently(task_count: int = 5) -> str:
    """
    Simulate running multiple async tasks concurrently.
    Shows that async tools don't block each other.
    """
    async def task(i: int) -> str:
        await asyncio.sleep(0.1 * i)
        return f"Task {i} done"

    results = await asyncio.gather(*[task(i) for i in range(task_count)])
    return "\n".join(results)

if __name__ == "__main__":
    mcp.run()
```

---

## Project 3: System Monitor Server

```python
# chapter03/system_monitor.py
from fastmcp import FastMCP
import os, platform, subprocess, time
from datetime import datetime
from typing import Literal

mcp = FastMCP("system-monitor")

@mcp.tool()
def get_system_info() -> dict:
    """Get OS, Python version, hostname, architecture, and uptime."""
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "hostname": platform.node(),
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "timestamp": datetime.now().isoformat(),
    }

@mcp.tool()
def get_disk_usage(path: str = "/") -> dict:
    """
    Get disk usage statistics for a given path.
    Returns total, used, free in GB and usage percentage.
    """
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bfree * stat.f_frsize
    used = total - free
    return {
        "path": path,
        "total_gb": round(total / 1024**3, 2),
        "used_gb": round(used / 1024**3, 2),
        "free_gb": round(free / 1024**3, 2),
        "percent_used": round((used / total) * 100, 1),
    }

@mcp.tool()
def get_cpu_and_memory() -> dict:
    """
    Get CPU and RAM usage. Requires psutil (pip install psutil).
    Returns percentages and raw values.
    """
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        return {
            "cpu_percent": cpu,
            "cpu_cores": psutil.cpu_count(),
            "ram_total_mb": round(mem.total / 1024**2),
            "ram_used_mb": round(mem.used / 1024**2),
            "ram_percent": mem.percent,
        }
    except ImportError:
        return {"error": "psutil not installed. Run: pip install psutil"}

@mcp.tool()
def list_processes(sort_by: Literal["cpu", "memory", "name"] = "cpu", limit: int = 10) -> str:
    """
    List running processes sorted by CPU, memory, or name.
    Returns a formatted table.
    """
    try:
        import psutil
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                procs.append(p.info)
            except Exception:
                pass

        key = {"cpu": "cpu_percent", "memory": "memory_percent", "name": "name"}[sort_by]
        reverse = sort_by != "name"
        procs = sorted(procs, key=lambda x: x.get(key) or 0, reverse=reverse)[:limit]

        lines = [f"{'PID':<8}{'CPU%':<8}{'MEM%':<8}NAME"]
        for p in procs:
            lines.append(f"{p['pid']:<8}{p['cpu_percent'] or 0:<8.1f}{p['memory_percent'] or 0:<8.1f}{p['name']}")
        return "\n".join(lines)
    except ImportError:
        return "psutil not installed. Run: pip install psutil"

@mcp.tool()
def run_safe_command(command: Literal["ls", "pwd", "date", "whoami", "uname", "uptime", "df", "env"]) -> str:
    """
    Run a safe read-only shell command. Only a fixed allowlist is permitted.
    Returns stdout output.
    """
    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
    return result.stdout.strip() or result.stderr.strip()

if __name__ == "__main__":
    mcp.run()
```

**Claude Desktop test:** *"Give me a full system health report."*

**Claude API test:**
```python
# chapter03/test_system_monitor.py
from anthropic import Anthropic
import json
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

# Import the tool functions directly for execution
import sys; sys.path.insert(0, ".")
from system_monitor import get_system_info, get_disk_usage, get_cpu_and_memory

tools = [
    {"name": "get_system_info", "description": "Get OS, Python version, hostname, architecture, and uptime.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_disk_usage", "description": "Get disk usage statistics.", "input_schema": {"type": "object", "properties": {"path": {"type": "string", "default": "/"}}}},
    {"name": "get_cpu_and_memory", "description": "Get CPU and RAM usage.", "input_schema": {"type": "object", "properties": {}}},
]

def execute_tool(name, args):
    if name == "get_system_info": return json.dumps(get_system_info())
    if name == "get_disk_usage": return json.dumps(get_disk_usage(**args))
    if name == "get_cpu_and_memory": return json.dumps(get_cpu_and_memory())
    return "Unknown tool"

messages = [{"role": "user", "content": "Give me a complete system health report."}]

while True:
    resp = client.messages.create(model="claude-opus-4-6", max_tokens=1024, tools=tools, messages=messages)
    if resp.stop_reason != "tool_use":
        print(resp.content[0].text)
        break
    messages.append({"role": "assistant", "content": resp.content})
    results = [{"type": "tool_result", "tool_use_id": b.id, "content": execute_tool(b.name, b.input)}
               for b in resp.content if b.type == "tool_use"]
    messages.append({"role": "user", "content": results})
```
