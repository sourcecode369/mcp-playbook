# Chapter 4 — Resources

## What Are Resources?

Resources are data the server exposes for reading. Unlike tools (actions), resources are content — files, records, config, live data. The LLM can read them as context.

## Static vs Dynamic Resources

```python
from fastmcp import FastMCP

mcp = FastMCP("resources-demo")

# Static: fixed URI, always the same resource
@mcp.resource("config://app")
def app_config() -> str:
    """Current application configuration."""
    return '{"version": "1.0", "debug": false}'

# Dynamic: URI template, resolves at read time
@mcp.resource("users://{user_id}/profile")
def user_profile(user_id: str) -> str:
    """Profile data for a specific user."""
    # user_id is extracted from the URI
    return f'{{"id": "{user_id}", "name": "User {user_id}"}}'
```

## Resource URI Design

Design URIs that are readable and hierarchical:
```
config://app/settings          → app configuration
db://mydb/tables/users         → database table
files:///home/user/notes       → filesystem path
github://repos/owner/repo      → GitHub resource
api://weather/current/london   → live API data
```

## Resource vs Tool Decision

| Scenario | Use |
|---|---|
| Read a known file or record | Resource |
| Search across files | Tool |
| Database record by ID | Resource |
| Run a SQL query | Tool |
| App config or schema | Resource |
| Send a message | Tool |

---

## Hands-On: Notes Resource Server

```python
# chapter04/notes_server.py
from fastmcp import FastMCP
import os, json
from pathlib import Path
from datetime import datetime

NOTES_DIR = Path.home() / "mcp-notes"
NOTES_DIR.mkdir(exist_ok=True)

mcp = FastMCP("notes")

# ─── Resources ────────────────────────────────────────────────────────────────

@mcp.resource("notes://index")
def list_notes() -> str:
    """Index of all notes with titles and modification dates."""
    notes = []
    for path in sorted(NOTES_DIR.glob("*.md")):
        stat = path.stat()
        notes.append({
            "id": path.stem,
            "title": path.stem.replace("-", " ").title(),
            "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
            "size": stat.st_size,
        })
    return json.dumps(notes, indent=2)

@mcp.resource("notes://{note_id}")
def get_note(note_id: str) -> str:
    """Read a specific note by its ID (filename without .md)."""
    path = NOTES_DIR / f"{note_id}.md"
    if not path.exists():
        return f"Note '{note_id}' not found."
    return path.read_text()

@mcp.resource("notes://search/{query}")
def search_notes(query: str) -> str:
    """Search note content for a query string. Returns matching note IDs and excerpts."""
    results = []
    for path in NOTES_DIR.glob("*.md"):
        content = path.read_text()
        if query.lower() in content.lower():
            idx = content.lower().find(query.lower())
            excerpt = content[max(0, idx-50):idx+100].strip()
            results.append({"id": path.stem, "excerpt": excerpt})
    return json.dumps(results, indent=2)

# ─── Tools ────────────────────────────────────────────────────────────────────

@mcp.tool()
def create_note(title: str, content: str) -> str:
    """Create a new markdown note. Title becomes the filename."""
    slug = title.lower().replace(" ", "-").replace("/", "-")
    path = NOTES_DIR / f"{slug}.md"
    header = f"# {title}\n\n*Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
    path.write_text(header + content)
    return f"Created note: {slug} ({len(content)} chars)"

@mcp.tool()
def update_note(note_id: str, content: str, append: bool = False) -> str:
    """
    Update an existing note. If append=True, add content to the end.
    If append=False, replace the entire content.
    """
    path = NOTES_DIR / f"{note_id}.md"
    if not path.exists():
        return f"Note '{note_id}' not found."
    if append:
        existing = path.read_text()
        path.write_text(existing + f"\n\n{content}")
        return f"Appended to {note_id}"
    path.write_text(content)
    return f"Updated {note_id}"

@mcp.tool()
def delete_note(note_id: str) -> str:
    """Permanently delete a note by ID."""
    path = NOTES_DIR / f"{note_id}.md"
    if not path.exists():
        return f"Note '{note_id}' not found."
    path.unlink()
    return f"Deleted: {note_id}"

if __name__ == "__main__":
    mcp.run()
```

**Test in Claude Desktop:**
1. *"Create a note called 'MCP Learning' with everything I know about resources."*
2. *"Show me all my notes."*
3. *"Search my notes for 'resources'."*
4. *"Append a summary section to my MCP Learning note."*

---

## Hands-On: Config & Schema Resources

```python
# chapter04/config_server.py
from fastmcp import FastMCP
import json, os
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP("config")

# Application config exposed as a resource
APP_CONFIG = {
    "app_name": "MyApp",
    "version": "2.1.0",
    "max_connections": 100,
    "features": {"dark_mode": True, "beta_features": False},
    "supported_languages": ["en", "es", "fr", "de", "ja"],
}

# Database schema exposed as a resource
DB_SCHEMA = {
    "users": {
        "columns": ["id", "email", "name", "created_at", "role"],
        "primary_key": "id",
        "indexes": ["email", "role"]
    },
    "orders": {
        "columns": ["id", "user_id", "total", "status", "created_at"],
        "primary_key": "id",
        "foreign_keys": {"user_id": "users.id"}
    }
}

@mcp.resource("config://app")
def get_app_config() -> str:
    """Current application configuration settings."""
    return json.dumps(APP_CONFIG, indent=2)

@mcp.resource("config://env/{key}")
def get_env_var(key: str) -> str:
    """
    Read a non-sensitive environment variable.
    Sensitive keys (containing TOKEN, SECRET, KEY, PASSWORD) are blocked.
    """
    blocked = ("TOKEN", "SECRET", "KEY", "PASSWORD", "CREDENTIAL")
    if any(b in key.upper() for b in blocked):
        return f"Access denied: '{key}' appears to be a sensitive variable."
    value = os.environ.get(key)
    if value is None:
        return f"Environment variable '{key}' is not set."
    return value

@mcp.resource("db://schema")
def get_db_schema() -> str:
    """Full database schema with table structures, columns, and relationships."""
    return json.dumps(DB_SCHEMA, indent=2)

@mcp.resource("db://schema/{table}")
def get_table_schema(table: str) -> str:
    """Schema for a specific database table."""
    if table not in DB_SCHEMA:
        return f"Table '{table}' not found. Available: {list(DB_SCHEMA.keys())}"
    return json.dumps({table: DB_SCHEMA[table]}, indent=2)

if __name__ == "__main__":
    mcp.run()
```

---

## Project 4: Local Knowledge Base with Resources + Tools

Build a server where every piece of knowledge is a resource (readable by URI) AND searchable/editable via tools.

**Requirements:**
- Resources: `kb://index`, `kb://topic/{topic}`, `kb://entry/{id}`
- Tools: `add_entry`, `search`, `update_entry`, `delete_entry`, `link_entries`
- Store data in a JSON file that persists across sessions
- Resources always return fresh data (read from file on every call)
- Test: add 10 entries, read them as resources, search, then update 3

```python
# chapter04/knowledge_base.py
from fastmcp import FastMCP
import json
from pathlib import Path
from datetime import datetime

DB_FILE = Path.home() / "mcp-kb.json"
mcp = FastMCP("knowledge-base")

def load_db() -> dict:
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return {"entries": {}, "next_id": 1}

def save_db(db: dict):
    DB_FILE.write_text(json.dumps(db, indent=2))

@mcp.resource("kb://index")
def kb_index() -> str:
    """Index of all knowledge base entries with IDs, topics, and titles."""
    db = load_db()
    entries = [
        {"id": k, "topic": v["topic"], "title": v["title"], "tags": v.get("tags", "")}
        for k, v in db["entries"].items()
    ]
    return json.dumps(sorted(entries, key=lambda x: x["topic"]), indent=2)

@mcp.resource("kb://topic/{topic}")
def kb_topic(topic: str) -> str:
    """All entries in a specific topic."""
    db = load_db()
    entries = {k: v for k, v in db["entries"].items() if v["topic"] == topic}
    return json.dumps(entries, indent=2)

@mcp.resource("kb://entry/{entry_id}")
def kb_entry(entry_id: str) -> str:
    """A specific knowledge base entry by ID."""
    db = load_db()
    entry = db["entries"].get(entry_id)
    if not entry:
        return f"Entry '{entry_id}' not found."
    return json.dumps(entry, indent=2)

@mcp.tool()
def add_entry(topic: str, title: str, content: str, tags: str = "") -> str:
    """Add a new entry to the knowledge base. Returns the new entry ID."""
    db = load_db()
    entry_id = str(db["next_id"])
    db["entries"][entry_id] = {
        "topic": topic,
        "title": title,
        "content": content,
        "tags": tags,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat(),
    }
    db["next_id"] += 1
    save_db(db)
    return f"Added entry #{entry_id}: {title}"

@mcp.tool()
def search(query: str, topic: str = "") -> str:
    """
    Search entries by text in title, content, or tags.
    Optionally filter by topic.
    """
    db = load_db()
    q = query.lower()
    results = []
    for entry_id, entry in db["entries"].items():
        if topic and entry["topic"] != topic:
            continue
        searchable = f"{entry['title']} {entry['content']} {entry.get('tags','')}".lower()
        if q in searchable:
            results.append(f"#{entry_id} [{entry['topic']}] {entry['title']}")
    return "\n".join(results) if results else "No results found."

@mcp.tool()
def update_entry(entry_id: str, content: str = None, tags: str = None) -> str:
    """Update an existing entry's content and/or tags."""
    db = load_db()
    if entry_id not in db["entries"]:
        return f"Entry #{entry_id} not found."
    if content: db["entries"][entry_id]["content"] = content
    if tags is not None: db["entries"][entry_id]["tags"] = tags
    db["entries"][entry_id]["updated"] = datetime.now().isoformat()
    save_db(db)
    return f"Updated entry #{entry_id}"

@mcp.tool()
def delete_entry(entry_id: str) -> str:
    """Delete a knowledge base entry by ID."""
    db = load_db()
    if entry_id not in db["entries"]:
        return f"Entry #{entry_id} not found."
    title = db["entries"][entry_id]["title"]
    del db["entries"][entry_id]
    save_db(db)
    return f"Deleted #{entry_id}: {title}"

if __name__ == "__main__":
    mcp.run()
```
