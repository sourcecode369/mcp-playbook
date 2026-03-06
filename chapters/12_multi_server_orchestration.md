# Chapter 12 — Multi-Server Orchestration

## Why Orchestrate Multiple Servers?

A single host can connect to many servers. Claude Desktop merges all tools into one pool. When building your own client, you need an orchestrator that:
- Connects to N servers simultaneously
- Merges all tools into one pool
- Routes each tool call to the right server
- Handles failures per-server without killing the whole system

---

## Orchestrator

```python
# chapter12/orchestrator.py
import asyncio, json, sys
from dataclasses import dataclass, field
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ServerConnection:
    name: str
    command: list[str]
    proc: asyncio.subprocess.Process = None
    tools: list[dict] = field(default_factory=list)
    _id: int = 0

    async def send(self, msg: dict):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()

    async def recv(self) -> dict:
        line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=30)
        return json.loads(line.decode())

    async def request(self, method: str, params: dict = None) -> dict:
        self._id += 1
        await self.send({"jsonrpc": "2.0", "id": self._id,
                         "method": method, "params": params or {}})
        while True:
            r = await self.recv()
            if r.get("id") == self._id:
                if "error" in r:
                    raise RuntimeError(str(r["error"]))
                return r.get("result", {})

class Orchestrator:
    def __init__(self):
        self.servers: list[ServerConnection] = []

    async def add_server(self, name: str, command: list[str]) -> None:
        conn = ServerConnection(name=name, command=command)
        conn.proc = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await conn.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "orchestrator", "version": "1.0.0"}
        })
        await conn.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        result = await conn.request("tools/list")
        conn.tools = result.get("tools", [])
        self.servers.append(conn)
        print(f"  [{name}] {len(conn.tools)} tools: {[t['name'] for t in conn.tools]}")

    def find_server(self, tool_name: str) -> ServerConnection | None:
        for s in self.servers:
            if any(t["name"] == tool_name for t in s.tools):
                return s
        return None

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        server = self.find_server(tool_name)
        if not server:
            return f"Error: no server has tool '{tool_name}'"
        result = await server.request("tools/call",
                                      {"name": tool_name, "arguments": arguments})
        return "\n".join(c["text"] for c in result.get("content", [])
                         if c.get("type") == "text")

    def all_tools_for_anthropic(self) -> list[dict]:
        tools = []
        for s in self.servers:
            for t in s.tools:
                tools.append({
                    "name": t["name"],
                    "description": f"[{s.name}] {t.get('description', '')}",
                    "input_schema": t.get("inputSchema", {"type": "object", "properties": {}})
                })
        return tools

    async def run_agent(self, user_message: str) -> str:
        """Run a single agent turn across all connected servers."""
        client = Anthropic()
        tools = self.all_tools_for_anthropic()
        messages = [{"role": "user", "content": user_message}]

        while True:
            resp = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                tools=tools,
                messages=messages
            )
            if resp.stop_reason != "tool_use":
                return next((b.text for b in resp.content if hasattr(b, "text")), "")

            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for b in resp.content:
                if b.type != "tool_use": continue
                server = self.find_server(b.name)
                print(f"  → [{server.name if server else '?'}] {b.name}({b.input})")
                result = await self.call_tool(b.name, b.input)
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": result})
            messages.append({"role": "user", "content": results})

    async def shutdown(self):
        for s in self.servers:
            s.proc.terminate()
            await s.proc.wait()
```

---

## Project 12: Three-Server Research Pipeline

Connect utility server + GitHub server + knowledge base. Run queries that require tools from all three.

```python
# chapter12/research_pipeline.py
import asyncio, sys
sys.path.insert(0, ".")
from orchestrator import Orchestrator

async def main():
    orch = Orchestrator()

    print("Connecting servers...")
    await orch.add_server("utilities", ["python", "../chapter02/utility_server.py"])
    await orch.add_server("github",    ["python", "../chapter09/github_server.py"])
    await orch.add_server("knowledge", ["python", "../chapter10/sqlite_server.py"])

    print(f"\nTotal tools available: {len(orch.all_tools_for_anthropic())}\n")

    queries = [
        # Uses utilities server
        "What is the SHA256 hash of 'model context protocol'?",

        # Uses GitHub server
        "How many stars does the anthropics/anthropic-sdk-python repo have?",

        # Uses knowledge base
        "Add a knowledge base entry: topic='MCP', title='Multi-Server Orchestration', "
        "content='Multiple MCP servers can be connected simultaneously. Each server runs "
        "as a subprocess. Tools from all servers are merged into one pool.'",

        # Multi-server: hash something, save to KB
        "Hash the string 'MCP rocks' with SHA256, then save it to the knowledge base "
        "as an entry with topic='experiments' and title='SHA256 test'.",
    ]

    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query[:80]}...")
        print('='*60)
        result = await orch.run_agent(query)
        print(f"Result: {result}")

    await orch.shutdown()

asyncio.run(main())
```

---

## Multi-Server Claude Desktop Config

```json
{
  "mcpServers": {
    "utilities": {
      "command": "python",
      "args": ["/path/to/chapter02/utility_server.py"]
    },
    "github": {
      "command": "python",
      "args": ["/path/to/chapter09/github_server.py"],
      "env": {"GITHUB_TOKEN": "ghp_xxx"}
    },
    "knowledge-base": {
      "command": "python",
      "args": ["/path/to/chapter10/sqlite_server.py"]
    },
    "dev-prompts": {
      "command": "python",
      "args": ["/path/to/chapter05/dev_prompts.py"]
    }
  }
}
```

With all four connected, Claude can:
- Use `/code_review` prompt (dev-prompts) to review code
- Search GitHub for similar patterns (github)
- Hash/encode strings (utilities)
- Save findings to the knowledge base (knowledge-base)

All in a single conversation, without you writing any routing logic.
