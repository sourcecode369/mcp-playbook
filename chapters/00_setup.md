# Chapter 0 — Setup & Hosts

## Install Everything

```bash
mkdir mcp-curriculum && cd mcp-curriculum
python -m venv .venv && source .venv/bin/activate

pip install fastmcp mcp anthropic httpx python-dotenv \
            starlette uvicorn pytest pytest-asyncio psutil
```

Create `.env`:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
GITHUB_TOKEN=ghp_your_token_here
```

---

## Host 1 — Claude Desktop (Interactive)

Claude Desktop is a host: it spawns your server as a child process and connects to it. You test your server by chatting.

**Install:** Download from claude.ai/download

**Config file location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Add a server:**
```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/absolute/path/to/server.py"],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx"
      }
    }
  }
}
```

Restart Claude Desktop after every config change. Tools appear automatically in chat.

**Subscription needed?**
- Free tier: works, limited messages per day
- Pro ($20/mo): recommended for development — no message caps during builds

---

## Host 2 — Claude API (Programmatic)

The Claude API lets you build your own client loop. You call Claude programmatically, handle tool_use responses, and route them to your MCP server or tool functions directly.

```python
# verify_api.py
import anthropic
from dotenv import load_dotenv

load_dotenv()
client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say hello in one word."}]
)
print(response.content[0].text)
```

**Subscription needed?**
- No subscription — pure pay-per-use
- Add credits at console.anthropic.com
- The entire curriculum costs roughly $5–10 in API calls

---

## The Full Picture

```
You (developer)
    │
    ├── Claude Desktop ──────────► python server.py
    │   (chat UI, visual)              (your FastMCP server)
    │
    └── Python script ──────────► anthropic.Anthropic()
        (your custom client)           (Claude API)
             │
             └── also spawns ────► python server.py
                                       (same server!)
```

The same FastMCP server works with both hosts. You don't change the server — you change how you connect to it.

---

## Hands-On: Verify Both Hosts Work

**Step 1 — Verify Python and packages**
```bash
python --version          # should be 3.10+
python -c "import fastmcp; print('FastMCP OK')"
python -c "import anthropic; print('Anthropic SDK OK')"
```

**Step 2 — Verify Claude Desktop**

Add this minimal server to your Claude Desktop config:
```json
{
  "mcpServers": {
    "hello": {
      "command": "python",
      "args": ["/absolute/path/to/hello_server.py"]
    }
  }
}
```

```python
# hello_server.py
from fastmcp import FastMCP

mcp = FastMCP("hello")

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}! MCP is working."

if __name__ == "__main__":
    mcp.run()
```

Restart Claude Desktop. Ask: *"Say hello to Alice using the hello tool."*

**Step 3 — Verify Claude API**
```python
# verify_tool_use.py
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()
client = Anthropic()

tools = [{
    "name": "hello",
    "description": "Say hello to someone.",
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"]
    }
}]

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=200,
    tools=tools,
    messages=[{"role": "user", "content": "Say hello to Bob."}]
)

for block in response.content:
    if block.type == "tool_use":
        print(f"Claude called: {block.name}({block.input})")
        # Execute the tool
        result = f"Hello, {block.input['name']}! MCP is working."
        print(f"Result: {result}")
```

Both should work before moving to Chapter 1.
