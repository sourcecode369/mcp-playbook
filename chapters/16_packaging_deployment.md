# Chapter 16 — Packaging & Deployment

## Project Structure

```
my-mcp-servers/
├── pyproject.toml
├── .env.example
├── README.md
├── Dockerfile
├── src/
│   └── my_mcp/
│       ├── __init__.py
│       ├── servers/
│       │   ├── utilities.py
│       │   ├── github.py
│       │   ├── knowledge_base.py
│       │   └── notes.py
│       └── shared/
│           ├── auth.py
│           └── validators.py
└── tests/
    ├── test_unit.py
    └── test_integration.py
```

---

## pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "my-mcp-servers"
version = "1.0.0"
description = "A production MCP server collection"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=0.4.0",
    "mcp>=1.0.0",
    "anthropic>=0.40.0",
    "httpx>=0.25.0",
    "python-dotenv>=1.0.0",
    "starlette>=0.36.0",
    "uvicorn>=0.27.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-asyncio>=0.23", "psutil"]

[project.scripts]
mcp-utilities    = "my_mcp.servers.utilities:run"
mcp-github       = "my_mcp.servers.github:run"
mcp-kb           = "my_mcp.servers.knowledge_base:run"
mcp-notes        = "my_mcp.servers.notes:run"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Entry Point Pattern

```python
# src/my_mcp/servers/utilities.py
from fastmcp import FastMCP
import argparse

mcp = FastMCP("utilities")

@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a safe mathematical expression."""
    ...

def run():
    """Entry point for CLI."""
    parser = argparse.ArgumentParser()
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

Install in dev mode:
```bash
pip install -e .

# Now works as CLI commands:
mcp-utilities
mcp-github
mcp-kb
```

Claude Desktop config (after install):
```json
{
  "mcpServers": {
    "utilities": {"command": "mcp-utilities"},
    "github": {
      "command": "mcp-github",
      "env": {"GITHUB_TOKEN": "ghp_xxx"}
    }
  }
}
```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

ENV MCP_ROOT=/data
RUN mkdir -p /data

# Run knowledge base server over SSE
EXPOSE 8080
ENTRYPOINT ["mcp-kb", "--transport", "sse", "--port", "8080"]
```

```bash
docker build -t my-mcp-servers .
docker run -p 8080:8080 -e GITHUB_TOKEN=xxx my-mcp-servers

# Claude Desktop:
# { "url": "http://localhost:8080/sse" }
```

---

## Deploy to Fly.io

```toml
# fly.toml
app = "my-mcp-servers"
primary_region = "iad"

[build]

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[env]
  PORT = "8080"

[[vm]]
  memory = "512mb"
  cpu_kind = "shared"
  cpus = 1
```

```bash
fly auth login
fly launch --no-deploy
fly secrets set GITHUB_TOKEN=xxx MCP_SECRET_TOKEN=xxx
fly deploy

# Connect Claude Desktop:
# { "url": "https://my-mcp-servers.fly.dev/sse",
#   "headers": {"Authorization": "Bearer xxx"} }
```

---

## Project 16: Package Your Best Server

Take the SQLite knowledge base from Chapter 10 and:

1. Move it into `src/my_mcp/servers/knowledge_base.py`
2. Add CLI entry point with `--transport` and `--port` arguments
3. Add to `pyproject.toml`
4. Write a `Dockerfile` that runs it over SSE on port 8080
5. Build and run the container locally
6. Verify Claude Desktop can connect to it at `http://localhost:8080/sse`
7. Add `requirements.txt` with pinned versions for reproducibility

```bash
# Final verification
docker build -t mcp-kb .
docker run -d -p 8080:8080 mcp-kb

# In Claude Desktop — add the SSE url and ask:
# "Add an entry to the knowledge base about Docker deployment"
# "Show me all knowledge base entries"
```
