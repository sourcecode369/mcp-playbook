import anthropic, json
from dotenv import load_dotenv
from pathlib import Path
from knowledge_base import add_entry, search, update_entry, delete_entry, kb_index, kb_topic, kb_entry

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

# Tools (add_entry, search, update_entry, delete_entry) are native MCP tools.
# Resources (kb_index, kb_topic, kb_entry) are MCP resources accessed via URIs in Claude Desktop.
# Here they are exposed as tools since the Claude API doesn't support MCP resources natively.

tools = [
    {
        "name": "add_entry",
        "description": "Add a new entry to the knowledge base. Returns the new entry ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "title": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string", "default": ""}
            },
            "required": ["topic", "title", "content"]
        }
    },
    {
        "name": "search",
        "description": "Search entries by text in title, content, or tags. Optionally filter by topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "topic": {"type": "string", "default": ""}
            },
            "required": ["query"]
        }
    },
    {
        "name": "update_entry",
        "description": "Update an existing entry's content and/or tags by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"},
                "content": {"type": "string"},
                "tags": {"type": "string"}
            },
            "required": ["entry_id"]
        }
    },
    {
        "name": "delete_entry",
        "description": "Delete a knowledge base entry by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"}
            },
            "required": ["entry_id"]
        }
    },
    {
        "name": "kb_index",
        "description": "List all knowledge base entries with IDs, topics, and titles.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "kb_topic",
        "description": "Get all entries under a specific topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string"}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "kb_entry",
        "description": "Read a specific knowledge base entry by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_id": {"type": "string"}
            },
            "required": ["entry_id"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "add_entry":    return add_entry(**args)
    if name == "search":       return search(**args)
    if name == "update_entry": return update_entry(**args)
    if name == "delete_entry": return delete_entry(**args)
    if name == "kb_index":     return kb_index()
    if name == "kb_topic":     return kb_topic(**args)
    if name == "kb_entry":     return kb_entry(**args)
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
    "Add 3 knowledge base entries about MCP: one about Tools (topic='mcp'), one about Resources (topic='mcp'), and one about Transports (topic='mcp').",
    "Show me all entries in the knowledge base.",
    "Search the knowledge base for entries about 'LLM'.",
    "Show me all entries under the 'mcp' topic.",
    "Update entry #1 to add the tag 'core-concept'.",
    "Read the full details of entry #2.",
    "Delete entry #3.",
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q[:80]}\n{'='*50}")
    print(chat_with_tools(q))
