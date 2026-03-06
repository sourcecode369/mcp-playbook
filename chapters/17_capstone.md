# Chapter 17 — Capstone: Personal AI Hub

## What You're Building

A single unified MCP server that integrates all concepts from this curriculum into one production-grade, deployable hub.

```
personal-ai-hub/
├── pyproject.toml
├── Dockerfile
├── .env.example
├── src/hub/
│   ├── __init__.py
│   ├── main.py              # entry point, FastMCP server
│   ├── modules/
│   │   ├── tasks.py         # todo list — SQLite, full CRUD
│   │   ├── journal.py       # daily journal — markdown files as resources
│   │   ├── bookmarks.py     # URL bookmarks — SQLite + FTS
│   │   ├── clipboard.py     # system clipboard read/write
│   │   └── timer.py         # focus timer with progress notifications
│   └── prompts/
│       ├── daily_review.py  # sampling-powered daily review
│       └── planning.py      # week planning prompt
└── tests/
    ├── test_unit.py
    └── test_integration.py
```

---

## Main Server

```python
# src/hub/main.py
from fastmcp import FastMCP
import argparse

mcp = FastMCP("personal-ai-hub")

# Import and register all modules
from hub.modules import tasks, journal, bookmarks, clipboard, timer
from hub.prompts import daily_review, planning

# Each module registers its tools/resources/prompts onto the same mcp instance
tasks.register(mcp)
journal.register(mcp)
bookmarks.register(mcp)
clipboard.register(mcp)
timer.register(mcp)
daily_review.register(mcp)
planning.register(mcp)

def run():
    parser = argparse.ArgumentParser(description="Personal AI Hub MCP Server")
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, port=args.port)

if __name__ == "__main__":
    run()
```

---

## Module Pattern

Each module uses a `register(mcp)` function to attach its tools/resources/prompts to the shared server:

```python
# src/hub/modules/tasks.py
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
import sqlite3, json
from pathlib import Path
from datetime import datetime
from typing import Literal

DB = Path.home() / "hub-tasks.db"

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                title    TEXT NOT NULL,
                done     INTEGER DEFAULT 0,
                priority TEXT DEFAULT 'medium',
                due_date TEXT,
                created  TEXT DEFAULT (datetime('now'))
            )
        """)

def register(mcp: FastMCP):
    init_db()

    @mcp.tool()
    def add_task(title: str,
                 priority: Literal["low", "medium", "high"] = "medium",
                 due_date: str = "") -> str:
        """Add a new task to the todo list."""
        with sqlite3.connect(DB) as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, priority, due_date) VALUES (?,?,?)",
                (title, priority, due_date)
            )
        return f"Added task #{cur.lastrowid}: {title}"

    @mcp.tool()
    def complete_task(task_id: int) -> str:
        """Mark a task as completed."""
        with sqlite3.connect(DB) as conn:
            conn.execute("UPDATE tasks SET done=1 WHERE id=?", (task_id,))
        return f"Completed task #{task_id}"

    @mcp.tool()
    def list_tasks(show_done: bool = False,
                   priority: str = "") -> str:
        """List tasks. By default shows only incomplete tasks."""
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM tasks WHERE 1=1"
            params = []
            if not show_done: sql += " AND done=0"
            if priority: sql += " AND priority=?"; params.append(priority)
            sql += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created"
            rows = conn.execute(sql, params).fetchall()
        if not rows:
            return "No tasks found."
        return "\n".join(
            f"{'✓' if r['done'] else '○'} #{r['id']} [{r['priority']}] {r['title']}"
            + (f" (due: {r['due_date']})" if r['due_date'] else "")
            for r in rows
        )

    @mcp.tool()
    def delete_task(task_id: int) -> str:
        """Delete a task permanently."""
        with sqlite3.connect(DB) as conn:
            conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        return f"Deleted task #{task_id}"

    @mcp.resource("tasks://today")
    def tasks_today() -> str:
        """All tasks due today or overdue."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(DB) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks WHERE done=0 AND (due_date <= ? OR due_date = '') ORDER BY priority",
                (today,)
            ).fetchall()
        return json.dumps([dict(r) for r in rows], indent=2, default=str)
```

---

## Requirements Checklist

Build all modules and verify each one:

- [ ] **Tasks**: `add_task`, `complete_task`, `list_tasks`, `delete_task`, `tasks://today` resource
- [ ] **Journal**: `write_journal`, `read_journal`, `journal://index` resource, `journal://{date}` resource
- [ ] **Bookmarks**: `save_bookmark`, `search_bookmarks`, `list_bookmarks`, FTS search
- [ ] **Clipboard**: `read_clipboard`, `write_clipboard` (use `pyperclip`)
- [ ] **Timer**: `start_timer(minutes)` with progress notifications, `stop_timer`
- [ ] **Daily Review prompt**: uses sampling to read tasks + journal then generate a daily summary
- [ ] **Planning prompt**: parameterized weekly planning template

**Minimum counts:**
- 15+ tools total
- 8+ resource URIs
- 2+ prompts (one must use sampling)
- All long-running tools use progress tokens
- Structured MCP logging in every module
- Rate limiting on all tools

---

## Integration Test

```python
# tests/test_integration.py
import asyncio, json, pytest

# Reuse MCPTestClient from chapter14
import sys; sys.path.insert(0, ".")
from chapter14.test_integration import MCPTestClient

@pytest.mark.asyncio
async def test_hub_has_all_expected_tools():
    async with MCPTestClient("src/hub/main.py") as c:
        tools = await c.list_tools()
        names = {t["name"] for t in tools}
        expected = {"add_task", "complete_task", "list_tasks",
                    "write_journal", "read_journal",
                    "save_bookmark", "search_bookmarks",
                    "start_timer"}
        for tool in expected:
            assert tool in names, f"Missing tool: {tool}"
        assert len(tools) >= 15

@pytest.mark.asyncio
async def test_hub_task_lifecycle():
    async with MCPTestClient("src/hub/main.py") as c:
        # Add
        result = await c.call_tool("add_task", {"title": "Test task", "priority": "high"})
        assert "Added" in result["content"][0]["text"]

        # List
        result = await c.call_tool("list_tasks", {})
        assert "Test task" in result["content"][0]["text"]

        # Complete
        result = await c.call_tool("complete_task", {"task_id": 1})
        assert "Completed" in result["content"][0]["text"]

@pytest.mark.asyncio
async def test_hub_resources():
    async with MCPTestClient("src/hub/main.py") as c:
        resources = await c.list_resources()
        uris = {r["uri"] for r in resources}
        assert "tasks://today" in uris

@pytest.mark.asyncio
async def test_hub_prompts():
    async with MCPTestClient("src/hub/main.py") as c:
        prompts = await c.list_prompts()
        names = {p["name"] for p in prompts}
        assert "daily_review" in names
        assert "planning" in names
```

---

## Deployment

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir -e .
EXPOSE 8080
ENTRYPOINT ["python", "-m", "hub.main", "--transport", "sse", "--port", "8080"]
```

```bash
docker build -t personal-ai-hub .
docker run -p 8080:8080 personal-ai-hub
```

Final Claude Desktop config:
```json
{
  "mcpServers": {
    "personal-hub-local": {
      "command": "python",
      "args": ["-m", "hub.main"]
    },
    "personal-hub-remote": {
      "url": "https://your-hub.fly.dev/sse",
      "headers": {"Authorization": "Bearer your-token"}
    }
  }
}
```

---

## What You've Built Across the Curriculum

| Chapter | Built |
|---|---|
| 01 | Protocol Explorer — raw JSON-RPC inspector |
| 02 | Utility Server — 5 tools with FastMCP |
| 03 | System Monitor — async tools, error handling |
| 04 | Notes + Knowledge Base — resources + tools |
| 05 | Dev Prompts — 6 developer workflow prompts |
| 06 | Weather Server — all 3 transports |
| 07 | Long-Running Task Server — progress + logging |
| 08 | Sampling Server — server-initiated LLM calls |
| 09 | GitHub Server — 10 tools, real API |
| 10 | SQLite Knowledge Base — FTS, resources, full CRUD |
| 11 | Custom Client + Claude API agent loop |
| 12 | Multi-Server Orchestrator |
| 13 | Secure Server — auth, rate limiting, audit log |
| 14 | Full test suite — unit + integration |
| 15 | MCP Inspector workflow + 5-bug debugging exercise |
| 16 | Packaged + Dockerized + Deployed server |
| 17 | Personal AI Hub — production multi-module server |
