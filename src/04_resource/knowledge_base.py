from fastmcp import FastMCP
import json
from pathlib import Path
from datetime import datetime

DB_FILE = Path.home() / "mcp-kb.json"
mcp = FastMCP("knowledge-base")

def load_db() -> str:
    if DB_FILE.exists():
        return json.loads(DB_FILE.read_text())
    return {"entries": {}, "next_id": 1}

def save_db(db: dict):
    DB_FILE.write_text(json.dumps(db, indent=2))
    
@mcp.resource("kb://index")
def kb_index() -> str:
    """
        Index of all knowledge base entries with IDs, topics, and titles.
    """
    
    db = load_db()
    entries = [
        {"id": k, "topic": v["topic"], "title": v["title"], "tags": v.get("tags", "")} for k, v in db["entries"].items()
    ]
    return json.dumps(sorted(entries, key=lambda x: x["topic"]), indent=2)

@mcp.resource("kb://topic/{topic}")
def kb_topic(topic: str) -> str:
    db = load_db()
    entries = {k:v for k, v in db['entries'].items() if v["topic"] == topic}
    return json.dumps(entries, indent=2)

@mcp.resource("kb://entry/{entry_id}")
def kb_entry(entry_id: str) -> str:
    """
        A specific knowledge base entry by ID.
    """
    db = load_db()
    entry = db["entries"].get(entry_id)
    if not entry:
        return f"Entry '{entry_id}' not found."
    return json.dumps(entry, indent=2)

@mcp.tool()
def add_entry(topic: str, title: str, content: str, tags: str= "") -> str:
    """
        Add a new entry to the knowledge base. Returns the new entry ID.
    """
    
    db = load_db()
    entry_id = str(db['next_id'])
    db['entries'][entry_id] = {
        "topic": topic,
        "title": title,
        "content": content,
        "tags": tags,
        "created": datetime.now().isoformat(),
        "updated": datetime.now().isoformat()
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