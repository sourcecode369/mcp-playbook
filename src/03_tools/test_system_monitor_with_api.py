import anthropic, json
from dotenv import load_dotenv
from pathlib import Path
from system_monitor import get_system_info, get_disk_usage, get_cpu_and_memory, list_processes, run_safe_command

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "get_system_info",
        "description": "Get OS, Python version, hostname, architecture and uptime.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_disk_usage",
        "description": "Get disk usage statistics for a given path. Returns total, used, free in GB and usage percentage.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "default": "/"}
            }
        }
    },
    {
        "name": "get_cpu_and_memory",
        "description": "Get CPU and RAM usage. Returns percentages and raw values.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_processes",
        "description": "List running processes sorted by CPU, memory, or name. Returns a formatted table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sort_by": {"type": "string", "enum": ["cpu", "memory", "name"], "default": "cpu"},
                "limit": {"type": "integer", "default": 10}
            }
        }
    },
    {
        "name": "run_safe_command",
        "description": "Run a safe read-only shell command. Allowed: ls, pwd, date, whoami, uname, uptime, df, env.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "enum": ["ls", "pwd", "date", "whoami", "uname", "uptime", "df", "env"]}
            },
            "required": ["command"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "get_system_info":   return json.dumps(get_system_info())
    if name == "get_disk_usage":    return json.dumps(get_disk_usage(**args))
    if name == "get_cpu_and_memory": return json.dumps(get_cpu_and_memory())
    if name == "list_processes":    return list_processes(**args)
    if name == "run_safe_command":  return run_safe_command(**args)
    return f"Unknown tool: {name}"

def chat_with_tools(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool called: {block.name}\t({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {str(result)[:120]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            return response.content[0].text


queries = [
    "Give me a full system health report — OS info, CPU, memory, and disk usage.",
    "What are the top 5 processes consuming the most memory right now?",
    "What is the current date and who am I logged in as?",
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q}\n{'='*50}")
    print(chat_with_tools(q))
