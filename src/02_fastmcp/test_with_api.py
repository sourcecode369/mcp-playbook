import anthropic
from dotenv import load_dotenv
import subprocess, json, asyncio
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "add",
        "description": "Add two numbers together.",
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"}
            },
            "required": ["a", "b"]
        }
    },
    {
        "name": "greet",
        "description": "Greet a person. Set formal=True for a professional greeting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "formal": {"type": "boolean", "default": False}
            },
            "required": ["name"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    """Execute a tool call by calling the actual function."""
    if name == "add":
        return str(args['a'] + args['b'])
    elif name == "greet":
        n, formal = args['name'], args.get("formal", False)
        return f"Good day, {n}." if formal else f"Hey {n}!"
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
                    print(f" Tool Called: {block.name}({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f" Result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id" : block.id,
                        "content": result
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            return response.content[0].text
        

print(chat_with_tools("Add 98 and 221"))
print(chat_with_tools("Greet Rohit formally"))
print(chat_with_tools("What is 122 plus 55 and then greet the number with name"))