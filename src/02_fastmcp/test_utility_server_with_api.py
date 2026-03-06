import anthropic, json
from dotenv import load_dotenv
from pathlib import Path
from utility_server import calculate, hash_text, encode_decode, count_words, timestamp

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

tools = [
    {
        "name": "calculate",
        "description": "Evaluate a safe mathematical expression. Supports: +, -, *, /, **, sqrt, log, sin, cos, pi, e. Example: 'sqrt(144) + 2**8'",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {"type": "string"}
            },
            "required": ["expression"]
        }
    },
    {
        "name": "hash_text",
        "description": "Hash a string using md5, sha1, sha256, or sha512. Returns the hex digest.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "algorithm": {"type": "string", "enum": ["md5", "sha1", "sha256", "sha512"], "default": "sha256"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "encode_decode",
        "description": "Base64 encode or decode a string.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "operation": {"type": "string", "enum": ["encode", "decode"], "default": "encode"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "count_words",
        "description": "Count words, characters, sentences, and unique words in text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "timestamp",
        "description": "Get the current timestamp. Format options: iso, unix, human, date, time.",
        "input_schema": {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["iso", "unix", "human", "date", "time"], "default": "iso"},
                "timezone": {"type": "string", "enum": ["utc", "local"], "default": "utc"}
            }
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "calculate":     return calculate(**args)
    if name == "hash_text":     return hash_text(**args)
    if name == "encode_decode": return encode_decode(**args)
    if name == "count_words":   return json.dumps(count_words(**args))
    if name == "timestamp":     return timestamp(**args)
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
                    print(f"  Tool called: {block.name}({block.input})")
                    result = run_tool(block.name, block.input)
                    print(f"  Result: {result}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            return response.content[0].text


queries = [
    "What is the square root of 1764 plus 2 to the power of 8?",
    "Hash 'Rohit Singh' using SHA256, then base64 encode the result.",
    "Decode this base64 string: SGVsbG8sIE1DUCBXb3JsZCE=",
    "Analyze this text and give me word and sentence counts: 'The quick brown fox jumps over the lazy dog. The dog did not care. The fox ran away.'",
    "What is today's date and the current unix timestamp?",
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q}\n{'='*50}")
    print(chat_with_tools(q))
