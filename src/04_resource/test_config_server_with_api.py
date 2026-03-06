import anthropic, json
from dotenv import load_dotenv
from pathlib import Path
from config_server import get_app_config, get_env_var, get_db_schema, get_table_schema

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

# All four are MCP resources (read-only, accessed via URIs in Claude Desktop).
# Exposed as tools here since the Claude API doesn't support MCP resources natively.

tools = [
    {
        "name": "get_app_config",
        "description": "Get the current application configuration settings.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_env_var",
        "description": "Read a non-sensitive environment variable. Sensitive keys (TOKEN, SECRET, KEY, PASSWORD) are blocked.",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Environment variable name"}
            },
            "required": ["key"]
        }
    },
    {
        "name": "get_db_schema",
        "description": "Get the full database schema with all tables, columns, and relationships.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_table_schema",
        "description": "Get the schema for a specific database table.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {"type": "string", "description": "Table name"}
            },
            "required": ["table"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "get_app_config":   return get_app_config()
    if name == "get_env_var":      return get_env_var(**args)
    if name == "get_db_schema":    return get_db_schema()
    if name == "get_table_schema": return get_table_schema(**args)
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
    "What is the current app version and what features are enabled?",
    "What tables exist in the database and what are their columns?",
    "Show me the full schema for the orders table.",
    "What is the HOME environment variable set to?",
    "Try to read the ANTHROPIC_API_KEY environment variable.",  # should be blocked
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q}\n{'='*50}")
    print(chat_with_tools(q))
