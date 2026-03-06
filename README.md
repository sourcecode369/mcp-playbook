# MCP Playbook

A hands-on Python curriculum for learning the Model Context Protocol (MCP) from the ground up — protocol internals, building real servers with FastMCP, connecting to Claude Desktop and the Claude API, and shipping production-grade tools.

---

## What You Will Build

- A raw protocol explorer that speaks JSON-RPC directly to a server
- A wire spy that intercepts and logs live Claude Desktop ↔ server traffic
- A GitHub integration server with 10 tools and real API calls
- A SQLite knowledge base with full-text search and resource URIs
- A custom MCP client backed by the Claude API
- A multi-server orchestrator that routes tool calls across servers
- A fully packaged, Dockerized, deployable production server

---

## Stack

| | |
|---|---|
| Server framework | FastMCP |
| Raw protocol | mcp Python SDK (Chapter 1 only) |
| LLM host — interactive | Claude Desktop |
| LLM host — programmatic | Claude API (`anthropic` SDK) |
| Transport | stdio · SSE · HTTP Streamable |
| External APIs | httpx |
| Database | sqlite3 |
| Testing | pytest + pytest-asyncio |
| Deployment | Docker · Fly.io |

---

## Quick Start

```bash
git clone https://github.com/sourcecode369/mcp-playbook.git
cd mcp-playbook/src

python -m venv .venv && source .venv/bin/activate
pip install fastmcp mcp anthropic httpx python-dotenv starlette uvicorn pytest pytest-asyncio

cp .env.example .env
# Add your ANTHROPIC_API_KEY and GITHUB_TOKEN to .env
```

Claude Desktop config:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

---

## Chapters

| # | Chapter | What You Build |
|---|---|---|
| 00 | [Setup & Hosts](chapters/00_setup.md) | Dev environment, verify Claude Desktop + API |
| 01 | [Protocol Foundations](chapters/01_protocol_foundations.md) | Protocol explorer, wire spy |
| 02 | [FastMCP Introduction](chapters/02_fastmcp_introduction.md) | First server, utility tools |
| 03 | [Tools](chapters/03_tools.md) | Async tools, error handling, system monitor |
| 04 | [Resources](chapters/04_resources.md) | Notes server, knowledge base |
| 05 | [Prompts](chapters/05_prompts.md) | Developer workflow prompt library |
| 06 | [Transports](chapters/06_transports.md) | stdio, SSE, HTTP — same server, three transports |
| 07 | [Notifications, Progress & Logging](chapters/07_notifications_progress_logging.md) | Progress tokens, structured MCP logs |
| 08 | [Sampling & Roots](chapters/08_sampling_roots.md) | Server-initiated LLM calls |
| 09 | [GitHub Server](chapters/09_github_server.md) | 10 tools + resources against real GitHub API |
| 10 | [SQLite Knowledge Base](chapters/10_sqlite_kb.md) | Full-text search, resource URIs, full CRUD |
| 11 | [Custom Client + Claude API](chapters/11_custom_client_claude_api.md) | MCP client backed by Claude API agent loop |
| 12 | [Multi-Server Orchestration](chapters/12_multi_server_orchestration.md) | Route across servers, three-server pipeline |
| 13 | [Auth & Security](chapters/13_auth_security.md) | OAuth SSE, rate limiting, audit logging |
| 14 | [Testing](chapters/14_testing.md) | Unit tests, integration tests, protocol compliance |
| 15 | [Inspector & Debugging](chapters/15_inspector_debugging.md) | MCP Inspector, wire spy, common errors |
| 16 | [Packaging & Deployment](chapters/16_packaging_deployment.md) | pyproject.toml, Docker, Fly.io |
| 17 | [Capstone](chapters/17_capstone.md) | Personal AI Hub — multi-module production server |

---

## Prerequisites

- Python 3.10+
- Basic async Python (`async/await`, `asyncio`)
- Familiarity with REST APIs
- Anthropic API key (pay-per-use, ~$5–10 covers the full curriculum)

---

## License

MIT
