# Model Context Protocol (MCP) — Crash Course

> Learn MCP inside out: protocol foundations, FastMCP, Claude Desktop & Claude API hosts, real projects, testing, and production deployment.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Server framework | **FastMCP** (`pip install fastmcp`) |
| Raw protocol (Ch 1) | `mcp` Python SDK |
| Host 1 — interactive | **Claude Desktop** |
| Host 2 — programmatic | **Claude API** (`anthropic` SDK) |
| Transport | stdio (local), SSE (remote) |
| HTTP | `starlette` + `uvicorn` |
| External APIs | `httpx` |
| Database | `sqlite3` (stdlib) |
| Testing | `pytest` + `pytest-asyncio` |
| Packaging | `hatchling` |

## Why Two Hosts?

- **Claude Desktop** — visual, interactive. Great for testing servers by chatting. Zero code needed to invoke tools.
- **Claude API** — programmatic. Build your own client loop, automate tests, integrate into apps.

Both use your servers unchanged. The server doesn't know or care which host connects to it.

## Subscription / Cost

| Surface | Cost |
|---|---|
| Claude Desktop | Free tier works. Pro ($20/mo) recommended for heavy development. |
| Claude API | Pay-per-use. No subscription. ~$5–10 API credits covers the entire curriculum. |

They bill separately. You can use one without the other.

## Setup

```bash
# Create workspace
mkdir mcp-curriculum && cd mcp-curriculum
python -m venv .venv && source .venv/bin/activate

# Install everything
pip install fastmcp mcp anthropic httpx python-dotenv \
            starlette uvicorn pytest pytest-asyncio psutil

# Create .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key-here" > .env
echo "GITHUB_TOKEN=ghp_your_token_here" >> .env
```

Claude Desktop config location:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

## Chapters

| # | Chapter | Key Skill |
|---|---|---|
| 00 | [Setup & Hosts](chapters/00_setup.md) | Environment, Claude Desktop, Claude API |
| 01 | [Protocol Foundations](chapters/01_protocol_foundations.md) | JSON-RPC, session lifecycle, raw protocol |
| 02 | [FastMCP Introduction](chapters/02_fastmcp_introduction.md) | FastMCP vs raw SDK, first server |
| 03 | [Tools](chapters/03_tools.md) | Decorators, type hints, error handling |
| 04 | [Resources](chapters/04_resources.md) | Static, dynamic, URI design |
| 05 | [Prompts](chapters/05_prompts.md) | Templates, multi-turn injection |
| 06 | [Transports](chapters/06_transports.md) | stdio, SSE, HTTP Streamable |
| 07 | [Notifications, Progress & Logging](chapters/07_notifications_progress_logging.md) | Progress tokens, MCP logging |
| 08 | [Sampling & Roots](chapters/08_sampling_roots.md) | Server-initiated LLM calls, filesystem roots |
| 09 | [Real Project — GitHub Server](chapters/09_github_server.md) | 10 tools + resources, real API |
| 10 | [Real Project — SQLite Knowledge Base](chapters/10_sqlite_kb.md) | FTS, resources, full CRUD |
| 11 | [Custom Client with Claude API](chapters/11_custom_client_claude_api.md) | Build a client, use anthropic SDK as LLM |
| 12 | [Multi-Server Orchestration](chapters/12_multi_server_orchestration.md) | Route across servers, aggregate tools |
| 13 | [Authentication & Security](chapters/13_auth_security.md) | API keys, OAuth SSE, rate limiting |
| 14 | [Testing](chapters/14_testing.md) | Unit tests, integration tests, protocol compliance |
| 15 | [MCP Inspector & Debugging](chapters/15_inspector_debugging.md) | Inspector tool, common errors, fixes |
| 16 | [Packaging & Deployment](chapters/16_packaging_deployment.md) | pyproject.toml, Docker, Fly.io |
| 17 | [Capstone](chapters/17_capstone.md) | Personal AI Hub — full production server |
