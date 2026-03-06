import anthropic, asyncio
from dotenv import load_dotenv
from pathlib import Path
from async_tools import fetch_multiple_urls, run_concurrently

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "fetch_multiple_urls",
        "description": "Fetch multiple URLs concurrently and return a summary. Much faster than fetching them one by one.",
        "input_schema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of URLs to fetch"
                }
            },
            "required": ["urls"]
        }
    },
    {
        "name": "run_concurrently",
        "description": "Simulate running multiple async tasks concurrently. Shows that async tools don't block each other.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_count": {
                    "type": "integer",
                    "description": "Number of concurrent tasks to run",
                    "default": 5
                }
            }
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "fetch_multiple_urls":
        return asyncio.run(fetch_multiple_urls(**args))
    if name == "run_concurrently":
        return asyncio.run(run_concurrently(**args))
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
                    print(f"  Tool called: {block.name}\t({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result:\n{result}\n")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            return response.content[0].text


queries = [
    "Fetch these 3 URLs concurrently and tell me which ones succeeded: https://httpbin.org/get, https://httpbin.org/status/404, https://httpbin.org/status/500",
    "Run 7 concurrent tasks and show me the results.",
    "Fetch https://httpbin.org/get and https://this-url-does-not-exist-xyz.com at the same time and compare what happened.",
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q}\n{'='*50}")
    print(chat_with_tools(q))
