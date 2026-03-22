from anthropic import Anthropic
import json
from dotenv import load_dotenv
import sys; sys.path.insert(0, ".")
from sqlite_server import add_entry, search, stats, get_entry, update_entry, delete_entry, link_entries, get_related, run_query

load_dotenv()
client = Anthropic()

tools = [
    {"name": "add_entry",
     "description": "Add a new knowledge base entry.",
     "input_schema": {"type": "object", "properties": {
         "topic": {"type": "string"}, "title": {"type": "string"},
         "content": {"type": "string"}, "tags": {"type": "string"}
     }, "required": ["topic", "title", "content"]}},
    {"name": "search",
     "description": "Full-text search across knowledge base.",
     "input_schema": {"type": "object", "properties": {
         "query": {"type": "string"}, "topic": {"type": "string"}
     }, "required": ["query"]}},
    {"name": "stats",
     "description": "Get knowledge base statistics.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_entry",
     "description": "Get a specific entry by its ID.",
     "input_schema": {"type": "object", "properties": {
         "entry_id": {"type": "integer"}
     }, "required": ["entry_id"]}},
    {"name": "update_entry",
     "description": "Update an existing entry. Only provided fields are changed.",
     "input_schema": {"type": "object", "properties": {
         "entry_id": {"type": "integer"}, "content": {"type": "string"},
         "tags": {"type": "string"}, "topic": {"type": "string"}
     }, "required": ["entry_id"]}},
    {"name": "delete_entry",
     "description": "Delete a knowledge base entry by ID.",
     "input_schema": {"type": "object", "properties": {
         "entry_id": {"type": "integer"}
     }, "required": ["entry_id"]}},
    {"name": "link_entries",
     "description": "Create a relationship link between two entries.",
     "input_schema": {"type": "object", "properties": {
         "from_id": {"type": "integer"}, "to_id": {"type": "integer"},
         "relation": {"type": "string"}
     }, "required": ["from_id", "to_id", "relation"]}},
    {"name": "get_related",
     "description": "Get all entries linked to a given entry (both directions).",
     "input_schema": {"type": "object", "properties": {
         "entry_id": {"type": "integer"}
     }, "required": ["entry_id"]}},
    {"name": "run_query",
     "description": "Run a read-only SELECT SQL query for custom analysis.",
     "input_schema": {"type": "object", "properties": {
         "sql": {"type": "string"}
     }, "required": ["sql"]}},
]

def execute(name, args):
    if name == "add_entry":    return add_entry(**args)
    if name == "search":       return search(**args)
    if name == "stats":        return stats()
    if name == "get_entry":    return get_entry(**args)
    if name == "update_entry": return update_entry(**args)
    if name == "delete_entry": return delete_entry(**args)
    if name == "link_entries": return link_entries(**args)
    if name == "get_related":  return get_related(**args)
    if name == "run_query":    return run_query(**args)
    return "Unknown tool"

def run_test(label: str, user_message: str):
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print('='*60)
    messages = [{"role": "user", "content": user_message}]
    while True:
        resp = client.messages.create(model="claude-opus-4-6", max_tokens=1024, tools=tools, messages=messages)
        if resp.stop_reason != "tool_use":
            print(resp.content[0].text)
            break
        messages.append({"role": "assistant", "content": resp.content})
        results = [{"type": "tool_result", "tool_use_id": b.id, "content": execute(b.name, b.input)}
                   for b in resp.content if b.type == "tool_use"]
        messages.append({"role": "user", "content": results})


# --- Test 1: Seed data + stats
run_test(
    "Seed entries and check stats",
    "Add 3 knowledge base entries about MCP: "
    "one about Tools, one about Resources, one about Transports. "
    "Then show me the stats."
)

# --- Test 2: Full-text search
run_test(
    "Full-text search",
    "Search the knowledge base for 'transport' and tell me what entries you find."
)

# --- Test 3: Topic-filtered search
run_test(
    "Topic-filtered search",
    "Search for 'MCP' but only within the topic 'MCP'. Show all matching entries."
)

# --- Test 4: Get a specific entry
run_test(
    "Get entry by ID",
    "Add an entry in topic 'testing' with title 'GetEntry Test' and content 'This entry tests get_entry.' "
    "Then fetch that same entry by its ID and show its full details."
)

# --- Test 5: Update an entry
run_test(
    "Update an entry",
    "Add an entry in topic 'testing' with title 'Update Test' and content 'Original content.' "
    "Then update that entry's content to 'Updated content.' and tags to 'updated,test'. "
    "Finally fetch it by ID to confirm the changes."
)

# --- Test 6: Link entries and get related
run_test(
    "Link entries and get related",
    "Add two entries: one titled 'Parent Concept' (topic='testing', content='This is the parent.') "
    "and one titled 'Child Concept' (topic='testing', content='This extends the parent.'). "
    "Link them with relation 'extends'. "
    "Then get the related entries for the parent and the child to confirm the link exists in both directions."
)

# --- Test 7: Delete an entry
run_test(
    "Delete an entry",
    "Add an entry in topic 'testing' with title 'To Be Deleted' and content 'This will be removed.' "
    "Then delete it by its ID. Finally search for 'To Be Deleted' to confirm it no longer appears."
)

# --- Test 8: Custom SQL query
run_test(
    "Custom SQL via run_query",
    "Run a SQL query to list all distinct topics in the knowledge base along with the count of entries per topic, "
    "ordered by count descending."
)