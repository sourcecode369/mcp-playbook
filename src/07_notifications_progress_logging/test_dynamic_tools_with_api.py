"""
Testing dynamic tools is different from other servers.
All tools are registered with FastMCP at startup, so the Claude API sees all three
(tool_a, tool_b, enable_tool) from the beginning.

The "dynamic" behaviour is about state: _enabled tracks which tools are active.
In a full MCP client, the server would send notifications/tools/list_changed
so the client could refresh its tool list mid-session.

With the raw Claude API we simulate this by:
1. Showing tool_a works before enabling tool_b
2. Calling enable_tool to update server state
3. Calling tool_b to confirm it now executes
4. Demonstrating the notifications that would fire in a real MCP session
"""
import anthropic
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

# Simulate the _enabled state from dynamic_tools.py
_enabled: set[str] = {"tool_a"}

tools = [
    {
        "name": "tool_a",
        "description": "Tool A - always available.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "tool_b",
        "description": "Tool B - only available when enabled.",
        "input_schema": {"type": "object", "properties": {}}
    },
    {
        "name": "enable_tool",
        "description": "Enable a tool by name so it becomes active.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Name of the tool to enable"}
            },
            "required": ["name"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    # Simulate tool logic directly — Context is only available inside FastMCP
    if name == "tool_a":
        return "Tool A result"
    if name == "tool_b":
        return "Tool B result"
    if name == "enable_tool":
        _enabled.add(args["name"])
        return f"Enabled tool: {args['name']}. Reconnect to see it."
    return f"Unknown tool: {name}"

def chat_with_tools(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            tools=tools,
            messages=messages
        )
        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool called: {block.name}({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {result}")
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": results})
        else:
            return response.content[0].text


# ─── Test 1: tool_a works without enabling anything ──────────────────────────
print("\n" + "="*50)
print("Test 1: Call tool_a (always available)")
print("="*50)
print(f"Enabled tools before: {_enabled}")
print(chat_with_tools("Run tool_a and tell me what it returns."))

# ─── Test 2: enable tool_b then call it ──────────────────────────────────────
print("\n" + "="*50)
print("Test 2: Enable tool_b, then call it")
print("="*50)
print(f"Enabled tools before: {_enabled}")
print(chat_with_tools("Enable tool_b, then run it and tell me what it returns."))
print(f"Enabled tools after: {_enabled}")

# ─── Test 3: demonstrate the notification that would fire in real MCP ─────────
print("\n" + "="*50)
print("Test 3: What happens in a real MCP session (Claude Desktop)")
print("="*50)
print("""
In Claude Desktop (full MCP protocol):
- When enable_tool() is called, the server would fire:
  notifications/tools/list_changed
- Claude Desktop receives this notification and calls tools/list again
- The refreshed tool list reflects the new _enabled state
- Claude can now call tool_b in subsequent turns

With the raw API we bypass this — all tools are in the tools list from the start.
The _enabled set controls whether the tool *logically* executes, not whether
the LLM can see it. To fully test dynamic tool lists you need the custom
MCP client from Chapter 11 which handles notifications.
""")
print(f"Final _enabled state: {_enabled}")
