import anthropic
from dotenv import load_dotenv
from pathlib import Path
from error_handling import safe_divide, fetch_url, parse_json

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "safe_divide",
        "description": "Divide a by b. Returns an error message if b is zero instead of crashing, so the LLM can recover gracefully.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "fetch_url",
        "description": "Fetch the content of a URL. Returns an error with details if the request fails.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "parse_json",
        "description": "Parse and pretty-print a JSON string. Returns a helpful error message if the JSON is invalid.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "safe_divide": return safe_divide(**args)
    if name == "fetch_url":   return fetch_url(**args)
    if name == "parse_json":  return parse_json(**args)
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

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Tool called: {block.name} \t ({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {result[:100]}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            return response.content[0].text


queries = [
    "Divide 100 by 0, and if that fails try dividing by 5 instead.",
    "Fetch the content of this URL: not-a-valid-url",
    'Parse this JSON: {"name": "Rohit", "role": "developer", "skills": ["MCP", "Python"]}',
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q}\n{'='*50}")
    print(chat_with_tools(q))
