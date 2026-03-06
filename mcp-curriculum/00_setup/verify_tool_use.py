import anthropic
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

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
    model="claude-sonnet-4-6",
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