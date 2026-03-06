import anthropic, json
from dotenv import load_dotenv
from pathlib import Path
from notes_server import create_note, update_note, delete_note, list_notes, get_note, search_notes

load_dotenv(Path(__file__).parent.parent / ".env", override=True)
client = anthropic.Anthropic()

# Resources (list_notes, get_note, search_notes) are read-only data in MCP.
# The Claude API only supports tools, so we expose them as tools here.
# In Claude Desktop they would be accessible as resources via their URIs.

tools = [
    {
        "name": "create_note",
        "description": "Create a new markdown note. Title becomes the filename.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["title", "content"]
        }
    },
    {
        "name": "update_note",
        "description": "Update an existing note. If append=True, add content to the end. If append=False, replace the content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {"type": "string", "description": "Note ID (filename without .md)"},
                "content": {"type": "string"},
                "append": {"type": "boolean", "default": False}
            },
            "required": ["note_id", "content"]
        }
    },
    {
        "name": "delete_note",
        "description": "Permanently delete a note by ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {"type": "string"}
            },
            "required": ["note_id"]
        }
    },
    {
        "name": "list_notes",
        "description": "List all notes with their IDs, titles, and modification dates.",
        "input_schema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "get_note",
        "description": "Read the full content of a specific note by its ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_id": {"type": "string"}
            },
            "required": ["note_id"]
        }
    },
    {
        "name": "search_notes",
        "description": "Search all notes for a query string. Returns matching note IDs and excerpts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }
]

def run_tool(name: str, args: dict) -> str:
    if name == "create_note":  return create_note(**args)
    if name == "update_note":  return update_note(**args)
    if name == "delete_note":  return delete_note(**args)
    if name == "list_notes":   return list_notes()
    if name == "get_note":     return get_note(**args)
    if name == "search_notes": return search_notes(**args)
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
    # Create a note
    "Create a note called 'MCP Resources' with this content: 'Resources are read-only data exposed by an MCP server. They are addressed by URIs like notes://index or notes://my-note. Unlike tools which perform actions, resources simply return data.'",

    # Append to it
    "Append this to the 'mcp-resources' note: 'Resources support dynamic URIs with parameters, e.g. notes://{note_id} where note_id is resolved at read time.'",

    # Create a second note
    "Create a note called 'MCP Tools' with content: 'Tools are functions that the LLM can call. They accept arguments and return results. Tools are for actions, resources are for data.'",

    # List all notes
    "List all my notes.",

    # Search across notes
    "Search my notes for the word 'LLM' and tell me which notes contain it.",

    # Read a specific note
    "Read the full content of the 'mcp-resources' note.",

    # Delete a note
    "Delete the 'mcp-tools' note.",
]

for q in queries:
    print(f"\n{'='*50}\nQ: {q[:80]}...\n{'='*50}")
    print(chat_with_tools(q))
