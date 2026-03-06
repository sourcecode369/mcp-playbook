# Chapter 13 — Authentication & Security

## Security Rules for MCP Servers

1. **Never trust tool arguments** — validate types, ranges, paths
2. **Enforce filesystem roots** — block `../` path traversal
3. **Use allowlists for shell commands** — never blocklists
4. **Rate limit external API calls** — per session, per tool
5. **Sanitize before SQL** — parameterized queries only
6. **Log all tool calls** — who called what with what args
7. **Principle of least privilege** — server only accesses what it needs

---

## Input Validation

```python
# chapter13/secure_server.py
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import os, re, time
from pathlib import Path
from collections import defaultdict

mcp = FastMCP("secure-demo")

# ─── Rate Limiting ─────────────────────────────────────────────────────────────

_call_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 30  # calls per 60 seconds

def check_rate_limit(tool_name: str):
    now = time.time()
    window = 60.0
    calls = [t for t in _call_log[tool_name] if now - t < window]
    _call_log[tool_name] = calls
    if len(calls) >= RATE_LIMIT:
        raise RuntimeError(f"Rate limit exceeded for '{tool_name}'. Try again in a minute.")
    _call_log[tool_name].append(now)

# ─── Path Safety ───────────────────────────────────────────────────────────────

SAFE_ROOT = Path(os.environ.get("MCP_ROOT", str(Path.home() / "mcp-safe"))).resolve()
SAFE_ROOT.mkdir(exist_ok=True)

def safe_path(user_path: str) -> Path:
    resolved = (SAFE_ROOT / user_path).resolve()
    if not str(resolved).startswith(str(SAFE_ROOT)):
        raise PermissionError(f"Path traversal blocked: {user_path!r}")
    return resolved

# ─── Input Validators ──────────────────────────────────────────────────────────

def validate_str(value: str, name: str, max_len: int = 1000, pattern: str = None) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    if len(value) > max_len:
        raise ValueError(f"{name} exceeds max length {max_len}")
    if pattern and not re.fullmatch(pattern, value):
        raise ValueError(f"{name} has invalid format")
    return value

def validate_int(value: int, name: str, min_val: int = None, max_val: int = None) -> int:
    if not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")
    if min_val is not None and value < min_val:
        raise ValueError(f"{name} must be >= {min_val}")
    if max_val is not None and value > max_val:
        raise ValueError(f"{name} must be <= {max_val}")
    return value

# ─── Secure Tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def read_file(path: str, ctx: Context) -> str:
    """Read a file from within the safe root directory."""
    check_rate_limit("read_file")
    validated = validate_str(path, "path", max_len=255)
    file_path = safe_path(validated)

    if not file_path.exists():
        return "File not found."
    if not file_path.is_file():
        return "Not a file."
    if file_path.stat().st_size > 1_000_000:
        return "File too large (>1MB)."

    await ctx.info(f"Reading: {file_path.name}")
    return file_path.read_text(encoding="utf-8", errors="replace")

@mcp.tool()
async def write_file(path: str, content: str, ctx: Context) -> str:
    """Write content to a file within the safe root directory."""
    check_rate_limit("write_file")
    validated_path = validate_str(path, "path", max_len=255)
    validated_content = validate_str(content, "content", max_len=100_000)
    file_path = safe_path(validated_path)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(validated_content)
    await ctx.info(f"Written: {file_path.name} ({len(validated_content)} bytes)")
    return f"Written {len(validated_content)} bytes to {file_path.name}"

if __name__ == "__main__":
    mcp.run()
```

---

## OAuth-Protected SSE Server

For remote servers exposed over HTTP, add Bearer token authentication:

```python
# chapter13/oauth_sse_server.py
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from mcp.server.sse import SseServerTransport
import uvicorn, os
from dotenv import load_dotenv

load_dotenv()
SECRET_TOKEN = os.getenv("MCP_SECRET_TOKEN", "change-me-in-production")

mcp = FastMCP("secure-remote")

@mcp.tool()
def whoami() -> str:
    """Returns confirmation that you are authenticated."""
    return "Authenticated successfully."

@mcp.tool()
def get_secret_data() -> str:
    """Returns sensitive data — only accessible with valid token."""
    return "This is protected data."

class BearerAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.url.path in ("/health",):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"error": "Missing Authorization: Bearer <token>"}, status_code=401)

        token = auth.removeprefix("Bearer ").strip()
        if token != SECRET_TOKEN:
            return JSONResponse({"error": "Invalid token"}, status_code=403)

        return await call_next(request)

sse = SseServerTransport("/messages/")

async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as (r, w):
        await mcp._mcp_server.run(r, w, mcp._mcp_server.create_initialization_options())

app = Starlette(routes=[
    Route("/health", endpoint=lambda r: JSONResponse({"status": "ok"})),
    Route("/sse", endpoint=handle_sse),
    Mount("/messages/", app=sse.handle_post_message),
])
app.add_middleware(BearerAuthMiddleware)

if __name__ == "__main__":
    print(f"Token: {SECRET_TOKEN}")
    uvicorn.run(app, host="0.0.0.0", port=8443)
```

Connect with token in Claude Desktop:
```json
{
  "mcpServers": {
    "secure-remote": {
      "url": "http://localhost:8443/sse",
      "headers": {
        "Authorization": "Bearer change-me-in-production"
      }
    }
  }
}
```

---

## Project 13: Audit-Logged Secure Server

Every tool call is logged with timestamp, tool name, arguments, and result. Build a server that wraps any FastMCP tool with automatic audit logging:

```python
# chapter13/audit_server.py
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import json, time
from pathlib import Path
from datetime import datetime
from functools import wraps

AUDIT_LOG = Path.home() / "mcp-audit.jsonl"
mcp = FastMCP("audit-demo")

def audit(func):
    """Decorator that logs every tool call to an audit log."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start = time.time()
        # Extract context if present
        ctx = kwargs.get("ctx") or next((a for a in args if hasattr(a, "info")), None)

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": func.__name__,
            "args": {k: v for k, v in kwargs.items() if k != "ctx"},
            "status": "started",
        }

        try:
            result = await func(*args, **kwargs)
            log_entry["status"] = "success"
            log_entry["duration_ms"] = round((time.time() - start) * 1000)
            if ctx:
                await ctx.info(f"Audit: {func.__name__} completed in {log_entry['duration_ms']}ms")
            return result
        except Exception as e:
            log_entry["status"] = "error"
            log_entry["error"] = str(e)
            log_entry["duration_ms"] = round((time.time() - start) * 1000)
            raise
        finally:
            with open(AUDIT_LOG, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

    return wrapper

@mcp.tool()
@audit
async def sensitive_operation(data: str, ctx: Context) -> str:
    """Perform a sensitive operation — fully audited."""
    return f"Processed: {data[:20]}..."

@mcp.tool()
@audit
async def delete_record(record_id: int, ctx: Context) -> str:
    """Delete a record — high-stakes, fully audited."""
    await ctx.warning(f"Deleting record #{record_id}")
    return f"Deleted record #{record_id}"

@mcp.tool()
def view_audit_log(last_n: int = 10) -> str:
    """View the last N entries from the audit log."""
    if not AUDIT_LOG.exists():
        return "No audit log yet."
    lines = AUDIT_LOG.read_text().strip().split("\n")
    entries = [json.loads(l) for l in lines[-last_n:] if l]
    return json.dumps(entries, indent=2)

if __name__ == "__main__":
    mcp.run()
```
