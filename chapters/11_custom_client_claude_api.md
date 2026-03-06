# Chapter 11 — Custom Client with Claude API

## Why Build a Custom Client?

Using Claude Desktop is convenient but opaque. Building your own client:
- Teaches you the exact request/response lifecycle
- Lets you use Claude API as the LLM backend (pay-per-use, no Desktop needed)
- Enables programmatic testing and automation
- Shows you how to build your own AI apps on top of MCP

## Architecture

```
Your Python Script (client)
    │
    ├── Spawns MCP server as subprocess
    ├── Sends initialize / tools/list / tools/call via stdin
    │
    └── Calls Anthropic API with:
        - Tool definitions (from MCP tools/list)
        - User message
        - Tool results (from MCP tools/call responses)
```

---

## Reusable MCP Client Class

```python
# chapter11/mcp_client.py
import asyncio, json, sys
from typing import Any

class MCPClient:
    """A minimal MCP client that connects to any stdio server."""

    def __init__(self, command: list[str]):
        self.command = command
        self.proc = None
        self._id = 0
        self.server_info = {}
        self.capabilities = {}

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    async def _send(self, msg: dict):
        raw = json.dumps(msg) + "\n"
        self.proc.stdin.write(raw.encode())
        await self.proc.stdin.drain()

    async def _recv(self) -> dict:
        line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=30)
        if not line:
            raise ConnectionError("Server closed connection")
        return json.loads(line.decode())

    async def _request(self, method: str, params: dict = None) -> Any:
        req_id = self._next_id()
        await self._send({"jsonrpc": "2.0", "id": req_id,
                          "method": method, "params": params or {}})
        while True:
            resp = await self._recv()
            if resp.get("id") == req_id:
                if "error" in resp:
                    raise RuntimeError(f"MCP error [{resp['error']['code']}]: {resp['error']['message']}")
                return resp.get("result", {})
            # Notification — handle or ignore
            if "method" in resp:
                self._on_notification(resp)

    def _on_notification(self, msg: dict):
        method = msg.get("method", "")
        if method == "notifications/message":
            p = msg.get("params", {})
            print(f"  [LOG/{p.get('level','?').upper()}] {p.get('data','')}", file=sys.stderr)

    async def connect(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        result = await self._request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
            "clientInfo": {"name": "custom-client", "version": "1.0.0"}
        })
        self.server_info = result.get("serverInfo", {})
        self.capabilities = result.get("capabilities", {})
        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def list_tools(self) -> list[dict]:
        return (await self._request("tools/list")).get("tools", [])

    async def call_tool(self, name: str, arguments: dict = None) -> str:
        result = await self._request("tools/call",
                                     {"name": name, "arguments": arguments or {}})
        return "\n".join(c["text"] for c in result.get("content", [])
                         if c.get("type") == "text")

    async def list_resources(self) -> list[dict]:
        return (await self._request("resources/list")).get("resources", [])

    async def read_resource(self, uri: str) -> str:
        result = await self._request("resources/read", {"uri": uri})
        return "\n".join(c.get("text", "") for c in result.get("contents", []))

    async def list_prompts(self) -> list[dict]:
        return (await self._request("prompts/list")).get("prompts", [])

    async def disconnect(self):
        if self.proc:
            self.proc.terminate()
            await self.proc.wait()

    def mcp_tools_to_anthropic(self, tools: list[dict]) -> list[dict]:
        """Convert MCP tool schemas to Anthropic API tool format."""
        return [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("inputSchema", {"type": "object", "properties": {}})
            }
            for t in tools
        ]
```

---

## Claude API + MCP Agent Loop

```python
# chapter11/claude_mcp_agent.py
"""
Full agent loop: Claude API as the LLM, MCP server for tools.
"""
import asyncio, sys
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp_client import MCPClient

load_dotenv()

async def run_agent(server_command: list[str], user_message: str) -> str:
    """
    Run a single-turn agent using Claude API + MCP server.
    Returns Claude's final response.
    """
    client = Anthropic()
    mcp = MCPClient(server_command)

    await mcp.connect()
    print(f"Connected to: {mcp.server_info.get('name')}", file=sys.stderr)

    # Get tools from MCP server, convert to Anthropic format
    mcp_tools = await mcp.list_tools()
    anthropic_tools = mcp.mcp_tools_to_anthropic(mcp_tools)
    print(f"Available tools: {[t['name'] for t in anthropic_tools]}", file=sys.stderr)

    messages = [{"role": "user", "content": user_message}]

    try:
        while True:
            resp = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1024,
                tools=anthropic_tools,
                messages=messages
            )

            if resp.stop_reason != "tool_use":
                # Claude is done — return final response
                final = next((b.text for b in resp.content
                              if hasattr(b, "text")), "")
                return final

            # Claude wants to call tools — add its response
            messages.append({"role": "assistant", "content": resp.content})

            # Execute each tool call via MCP
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                print(f"  → Calling: {block.name}({block.input})", file=sys.stderr)
                result = await mcp.call_tool(block.name, block.input)
                print(f"  ← Result: {result[:100]}...", file=sys.stderr)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

            messages.append({"role": "user", "content": tool_results})

    finally:
        await mcp.disconnect()

async def main():
    if len(sys.argv) < 3:
        print("Usage: python claude_mcp_agent.py <server.py> 'your question'")
        sys.exit(1)

    server_script = sys.argv[1]
    question = sys.argv[2]

    result = await run_agent(["python", server_script], question)
    print("\n" + "="*50)
    print("FINAL RESPONSE:")
    print("="*50)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

Usage:
```bash
# Test with your utility server
python chapter11/claude_mcp_agent.py chapter02/utility_server.py "Hash my email address and encode the result in base64"

# Test with GitHub server
python chapter11/claude_mcp_agent.py chapter09/github_server.py "List the top 5 repos for the anthropics org"

# Test with knowledge base
python chapter11/claude_mcp_agent.py chapter10/sqlite_server.py "Add an entry about MCP Tools and then show me the stats"
```

---

## Interactive Shell Client

```python
# chapter11/interactive_shell.py
"""
Interactive REPL: connect to any MCP server and explore it.
"""
import asyncio, json, sys
from mcp_client import MCPClient

async def shell(server_command: list[str]):
    mcp = MCPClient(server_command)
    await mcp.connect()

    print(f"Connected to: {mcp.server_info.get('name')} v{mcp.server_info.get('version')}")
    print("Commands: tools, call <name> [json_args], resources, read <uri>, prompts, quit\n")

    while True:
        try:
            line = input("mcp> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line: continue
        parts = line.split(" ", 2)
        action = parts[0].lower()

        try:
            if action == "quit": break
            elif action == "tools":
                for t in await mcp.list_tools():
                    print(f"  {t['name']}: {t.get('description','')[:80]}")
            elif action == "call" and len(parts) >= 2:
                args = json.loads(parts[2]) if len(parts) > 2 else {}
                print(await mcp.call_tool(parts[1], args))
            elif action == "resources":
                for r in await mcp.list_resources():
                    print(f"  {r['uri']}: {r.get('name','')}")
            elif action == "read" and len(parts) >= 2:
                print((await mcp.read_resource(parts[1]))[:3000])
            elif action == "prompts":
                for p in await mcp.list_prompts():
                    print(f"  {p['name']}: {p.get('description','')}")
            else:
                print("Unknown command.")
        except Exception as e:
            print(f"Error: {e}")

    await mcp.disconnect()
    print("Disconnected.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python interactive_shell.py <server.py>")
        sys.exit(1)
    asyncio.run(shell(["python", sys.argv[1]]))
```

Usage:
```bash
python chapter11/interactive_shell.py chapter02/utility_server.py

mcp> tools
mcp> call calculate {"expression": "sqrt(144) + 2**8"}
mcp> call hash_text {"text": "hello world", "algorithm": "sha256"}
mcp> quit
```

---

## Project 11: Multi-Turn Conversation Agent

Extend the agent loop to support multi-turn conversations (the user can keep chatting):

```python
# chapter11/multi_turn_agent.py
import asyncio, sys
from anthropic import Anthropic
from dotenv import load_dotenv
from mcp_client import MCPClient

load_dotenv()

async def chat(server_command: list[str]):
    client = Anthropic()
    mcp = MCPClient(server_command)
    await mcp.connect()

    mcp_tools = await mcp.list_tools()
    tools = mcp.mcp_tools_to_anthropic(mcp_tools)
    messages = []

    print(f"Chatting with: {mcp.server_info.get('name')}")
    print(f"Tools: {[t['name'] for t in tools]}")
    print("Type 'quit' to exit.\n")

    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ("quit", "exit", "q"): break
            if not user_input: continue

            messages.append({"role": "user", "content": user_input})

            while True:
                resp = client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=1024,
                    tools=tools,
                    messages=messages
                )
                if resp.stop_reason != "tool_use":
                    final = next((b.text for b in resp.content if hasattr(b, "text")), "")
                    messages.append({"role": "assistant", "content": final})
                    print(f"Claude: {final}\n")
                    break

                messages.append({"role": "assistant", "content": resp.content})
                results = []
                for b in resp.content:
                    if b.type != "tool_use": continue
                    print(f"  [tool] {b.name}({b.input})")
                    result = await mcp.call_tool(b.name, b.input)
                    results.append({"type": "tool_result", "tool_use_id": b.id, "content": result})
                messages.append({"role": "user", "content": results})

    finally:
        await mcp.disconnect()

if __name__ == "__main__":
    asyncio.run(chat(["python", sys.argv[1] if len(sys.argv) > 1 else "chapter10/sqlite_server.py"]))
```
