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