"""
Test weather_server.py via Claude API + stdio transport.
The server is spawned as a subprocess (stdio) — same as Claude Desktop does it.
"""
import anthropic, json
from dotenv import load_dotenv
from pathlib import Path
from weather_server import get_weather, compare_weather, list_available_cities

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city. Returns temperature, humidity, and conditions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "compare_weather",
        "description": "Compare weather between two cities side by side.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city1": {"type": "string"},
                "city2": {"type": "string"}
            },
            "required": ["city1", "city2"]
        }
    },
    {
        "name": "list_available_cities",
        "description": "List all cities with weather data available.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "get_weather":          return get_weather(**args)
    if name == "compare_weather":      return compare_weather(**args)
    if name == "list_available_cities": return list_available_cities()
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
    "What cities do you have weather data for?",
    "What is the weather like in Tokyo right now?",
    "Compare the weather in London and Paris. Which one is warmer?",
    "Give me a full weather report for all available cities.",
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q}\n{'='*50}")
    print(chat_with_tools(q))
