# Chapter 7 — Notifications, Progress & Logging

## What Are Notifications?

So far every interaction has been request → response: the client asks, the server answers. But sometimes the server needs to send a message the client didn't ask for — that's a notification.

Notifications are one-way messages with no response expected. The server fires them and moves on. They're used for:
- **Logging**: telling the client what the server is doing internally
- **Progress**: telling the client how far along a long-running task is
- **Change events**: telling the client something changed (tool list, resource content, etc.)

Notifications are JSON-RPC messages without an `id` field — that's what distinguishes them from requests.

```json
// This is a notification (no "id")
{
  "jsonrpc": "2.0",
  "method": "notifications/message",
  "params": {
    "level": "info",
    "data": "Processing started",
    "logger": "my-tool"
  }
}
```

## Notification Types

| Notification | Direction | Purpose |
|---|---|---|
| `notifications/message` | Server→Client | Structured log (info/warning/error/debug) |
| `notifications/progress` | Server→Client | Progress update for long-running tool |
| `notifications/tools/list_changed` | Server→Client | Tool list changed dynamically |
| `notifications/resources/list_changed` | Server→Client | Resource list changed |
| `notifications/resources/updated` | Server→Client | Specific resource was updated |
| `notifications/cancelled` | Either | Request was cancelled |

## Why This Matters

Without notifications, a 30-second tool call is a black box — the client sees nothing until it completes. With notifications:
- **Progress**: the user sees a progress bar or percentage
- **Logging**: developers see what the server is doing in real time
- **Debugging**: you can trace exactly what happened inside a tool

Claude Desktop displays `notifications/message` logs in the chat UI. When your tool calls `ctx.info("Starting scan...")`, users see it appear as the tool runs.

## How Context Works

The `Context` object is FastMCP's way of giving your tool access to notification APIs. You don't construct it yourself — FastMCP injects it when it sees a `ctx: Context` parameter:

```python
from fastmcp.server.fastmcp import Context

@mcp.tool()
async def my_tool(input: str, ctx: Context) -> str:
    # ctx is automatically injected by FastMCP
    # You just declare it as a parameter
    await ctx.info("Tool started")
    ...
```

FastMCP looks at your function signature, sees `ctx: Context`, and injects the live request context. If you don't declare it, you don't get it. If you declare it, it's always there.

## Log Levels

```python
await ctx.debug("Detailed diagnostic info — only useful during development")
await ctx.info("Normal operational messages — what the tool is doing")
await ctx.warning("Something unexpected but recoverable happened")
await ctx.error("Something failed — the tool may still complete")
```

Level hierarchy: `debug` < `info` < `warning` < `error`

Clients can filter by level. Claude Desktop shows all levels by default.

## MCP Logging

FastMCP gives you access to the request context for sending log messages to the client:

```python
from fastmcp import FastMCP
from mcp.server.fastmcp import Context

mcp = FastMCP("logging-demo")

@mcp.tool()
async def process_data(input: str, ctx: Context) -> str:
    """Process data with structured logging."""
    await ctx.info("Starting processing...")
    await ctx.debug(f"Input length: {len(input)}")

    if not input.strip():
        await ctx.warning("Empty input received")
        return "Nothing to process."

    # Do work
    result = input.upper()
    await ctx.info(f"Processing complete. Output: {len(result)} chars")
    return result
```

The `Context` parameter is injected by FastMCP — just add it to your function signature. FastMCP detects it automatically.

## Progress Tokens

### How Progress Works

When a client wants progress updates, it sends a `progressToken` in the request's `_meta` field:

```json
{
  "method": "tools/call",
  "params": {
    "name": "slow_tool",
    "arguments": {},
    "_meta": { "progressToken": "abc-123" }
  }
}
```

The server then sends `notifications/progress` messages using that token:

```json
{
  "method": "notifications/progress",
  "params": {
    "progressToken": "abc-123",
    "progress": 45,
    "total": 100
  }
}
```

The client matches the `progressToken` to know which tool the progress belongs to. FastMCP handles all of this for you via `ctx.report_progress()`.

For long-running tools, the client sends a `progressToken` and your server sends progress notifications back:

```python
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import asyncio

mcp = FastMCP("progress-demo")

@mcp.tool()
async def batch_process(
    items: list[str],
    ctx: Context
) -> str:
    """Process a list of items with progress updates."""
    total = len(items)
    results = []

    for i, item in enumerate(items, 1):
        await asyncio.sleep(0.2)  # simulate work
        results.append(item.upper())

        # Report progress
        await ctx.report_progress(progress=i, total=total)
        await ctx.info(f"Processed: {item}")

    return f"Done. Processed {total} items: {', '.join(results)}"
```

---

## Hands-On: Dynamic Tool List

```python
# chapter07/dynamic_tools.py
from fastmcp import FastMCP
from mcp.server.fastmcp import Context

mcp = FastMCP("dynamic-tools")

_enabled: set[str] = {"tool_a"}

@mcp.tool()
async def tool_a(ctx: Context) -> str:
    """Tool A — always available."""
    await ctx.info("Tool A executed")
    return "Tool A result"

@mcp.tool()
async def tool_b(ctx: Context) -> str:
    """Tool B — only available when enabled."""
    await ctx.info("Tool B executed")
    return "Tool B result"

@mcp.tool()
async def enable_tool(name: str, ctx: Context) -> str:
    """Enable a tool by name. Notifies the client that the tool list changed."""
    _enabled.add(name)
    await ctx.info(f"Enabled: {name}")
    # Notify client — Claude Desktop will refresh its tool list
    # await ctx.session.send_tool_list_changed()
    return f"Enabled tool: {name}. Reconnect to see it."

if __name__ == "__main__":
    mcp.run()
```

---

## Project 7: Long-Running Task Server

Build a server where every tool reports progress and uses structured logging. Test with both Claude Desktop (see logs in UI) and Claude API (capture log notifications).

```python
# chapter07/long_running_server.py
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import asyncio, random, json
from datetime import datetime

mcp = FastMCP("long-running-tasks")

@mcp.tool()
async def scan_directory(path: str, ctx: Context) -> str:
    """
    Simulate scanning a directory tree with progress updates.
    Reports each subdirectory as it's scanned.
    """
    import os
    await ctx.info(f"Starting directory scan: {path}")

    if not os.path.exists(path):
        await ctx.warning(f"Path does not exist: {path}")
        return f"Directory not found: {path}"

    files = []
    dirs = []
    all_items = list(os.walk(path))
    total = len(all_items)

    for i, (root, subdirs, filenames) in enumerate(all_items, 1):
        await asyncio.sleep(0.05)  # simulate IO
        files.extend(filenames)
        dirs.append(root)
        await ctx.report_progress(progress=i, total=total)

        if i % 5 == 0:
            await ctx.debug(f"Scanned {i}/{total} directories, {len(files)} files so far")

    await ctx.info(f"Scan complete: {len(dirs)} dirs, {len(files)} files")
    return json.dumps({
        "path": path,
        "total_directories": len(dirs),
        "total_files": len(files),
        "scan_time": datetime.now().isoformat()
    }, indent=2)

@mcp.tool()
async def simulate_training(
    epochs: int,
    ctx: Context
) -> str:
    """
    Simulate an ML training run with per-epoch progress and metrics.
    epochs: number of training epochs (1-20)
    """
    epochs = max(1, min(20, epochs))
    await ctx.info(f"Starting training run: {epochs} epochs")

    log = []
    for epoch in range(1, epochs + 1):
        await asyncio.sleep(0.4)

        # Fake metrics that improve over time
        loss = round(1.0 / (epoch * 0.5 + 0.1) + random.uniform(-0.05, 0.05), 4)
        acc = round(1.0 - loss * 0.5, 4)
        log.append({"epoch": epoch, "loss": loss, "accuracy": acc})

        await ctx.report_progress(progress=epoch, total=epochs)
        await ctx.info(f"Epoch {epoch}/{epochs} — loss: {loss:.4f}, acc: {acc:.4f}")

        if loss > 1.5:
            await ctx.warning(f"High loss at epoch {epoch}: {loss:.4f}")

    best = min(log, key=lambda x: x["loss"])
    await ctx.info(f"Training complete. Best epoch: {best['epoch']} (loss={best['loss']:.4f})")
    return json.dumps({"epochs_run": epochs, "final_loss": log[-1]["loss"],
                       "best_epoch": best, "history": log}, indent=2)

@mcp.tool()
async def process_batch(
    batch_size: int,
    fail_rate: float,
    ctx: Context
) -> str:
    """
    Process a batch of items, with some items failing (for testing error logging).
    batch_size: number of items (1-50)
    fail_rate: fraction of items that fail (0.0-1.0)
    """
    batch_size = max(1, min(50, batch_size))
    fail_rate = max(0.0, min(1.0, fail_rate))

    await ctx.info(f"Processing batch of {batch_size} items (fail rate: {fail_rate:.0%})")

    succeeded, failed = 0, 0
    for i in range(1, batch_size + 1):
        await asyncio.sleep(0.1)
        if random.random() < fail_rate:
            failed += 1
            await ctx.warning(f"Item {i} failed")
        else:
            succeeded += 1
        await ctx.report_progress(progress=i, total=batch_size)

    level = "info" if failed == 0 else "warning" if failed < batch_size // 2 else "error"
    msg = f"Batch done: {succeeded} succeeded, {failed} failed"
    if level == "info": await ctx.info(msg)
    elif level == "warning": await ctx.warning(msg)
    else: await ctx.error(msg)

    return json.dumps({"total": batch_size, "succeeded": succeeded,
                       "failed": failed, "success_rate": f"{succeeded/batch_size:.0%}"})

if __name__ == "__main__":
    mcp.run()
```

---

## What You'll See in Claude Desktop

When your tools send notifications, Claude Desktop shows them in real time:

- **`ctx.info()`** — appears as a small status message below the tool call
- **`ctx.warning()`** — appears highlighted in amber
- **`ctx.error()`** — appears highlighted in red
- **`ctx.report_progress()`** — appears as a progress bar (if the client supports it)

This makes long-running tools feel responsive. Instead of the user staring at a spinner for 30 seconds, they see each step as it happens.

---

## When to Use Each

| Scenario | Use |
|---|---|
| Tool starts, doing initial setup | `ctx.info()` |
| Iterating over items (1 of 50...) | `ctx.report_progress()` + `ctx.debug()` |
| Input looks suspicious but recoverable | `ctx.warning()` |
| A sub-step failed but tool continues | `ctx.error()` |
| Diagnostic details for debugging | `ctx.debug()` |
| Tool completes successfully | `ctx.info()` with summary |

---

**Claude API test — capture log notifications:**
```python
# chapter07/test_with_logs.py
"""
Test long-running tools via Claude API and capture MCP log notifications.
"""
from anthropic import Anthropic
from dotenv import load_dotenv
import sys, os

# Import tool functions directly
sys.path.insert(0, ".")

load_dotenv()
client = Anthropic()

tools = [
    {
        "name": "simulate_training",
        "description": "Simulate an ML training run with per-epoch progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "epochs": {"type": "integer", "description": "Number of epochs (1-20)"}
            },
            "required": ["epochs"]
        }
    }
]

async def run_training(epochs: int) -> str:
    """Run training directly (simulated, no MCP transport needed for API test)."""
    import asyncio
    log = []
    for epoch in range(1, epochs + 1):
        loss = round(1.0 / (epoch * 0.5 + 0.1), 4)
        acc = round(1.0 - loss * 0.5, 4)
        log.append(f"Epoch {epoch}/{epochs} — loss: {loss:.4f}, acc: {acc:.4f}")
    return "\n".join(log)

import asyncio

messages = [{"role": "user", "content": "Train a model for 5 epochs and summarize the results."}]
while True:
    resp = client.messages.create(model="claude-opus-4-6", max_tokens=1024, tools=tools, messages=messages)
    if resp.stop_reason != "tool_use":
        print(resp.content[0].text)
        break
    messages.append({"role": "assistant", "content": resp.content})
    results = []
    for b in resp.content:
        if b.type == "tool_use":
            result = asyncio.run(run_training(b.input["epochs"]))
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": result})
    messages.append({"role": "user", "content": results})
```
