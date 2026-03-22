from fastmcp import FastMCP
import sqlite3, json
from pathlib import Path
from datetime import datetime
from typing import Literal

DB_PATH = Path.home() / "mcp-knowledge.db"
mcp = FastMCP("sqlite-kb")

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS entries (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                topic   TEXT NOT NULL,
                title   TEXT NOT NULL,
                content TEXT NOT NULL,
                tags    TEXT DEFAULT '',
                source  TEXT DEFAULT '',
                created TEXT DEFAULT (datetime('now')),
                updated TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS links (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                from_id  INTEGER REFERENCES entries(id) ON DELETE CASCADE,
                to_id    INTEGER REFERENCES entries(id) ON DELETE CASCADE,
                relation TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_topic ON entries(topic);
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
                USING fts5(title, content, tags, content='entries', content_rowid='id');
            CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
                INSERT INTO entries_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
                INSERT INTO entries_fts(entries_fts, rowid, title, content, tags)
                VALUES ('delete', old.id, old.title, old.content, old.tags);
                INSERT INTO entries_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
                INSERT INTO entries_fts(entries_fts, rowid, title, content, tags)
                VALUES ('delete', old.id, old.title, old.content, old.tags);
            END;
        """
        )
        
init_db()


# -------- Resources
@mcp.resource("kb://schema")
def schema() -> str:
    """Database schema - tables, columns, indexes."""
    with get_db() as conn:
        rows = conn.execute("SELECT sql from sqlite_master WHERE type='table'").fetchall()
        return "\n\n".join(r["sql"] for r in rows if r["sql"])
    
@mcp.resource("kb://topics")
def topics() -> str:
    """All topics with entry counts."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT topic, COUNT(*) as count FROM entries GROUP BY topic ORDER BY count DESC"
        ).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2)

@mcp.resource("kb://topic/{topic}")
def topic_entries(topic: str) -> str:
    """All entries in a specific topic."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM entries WHERE topic = ? ORDER BY updated DESC", (topic,)
        ).fetchall()
    return json.dumps([dict(r) for r in rows], indent=2, default=str)

@mcp.resource("kb://entry/{entry_id}")
def entry_detail(entry_id: str) -> str:
    """A specific entry with all its fields."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        return f"Entry #{entry_id} not found."
    return json.dumps(dict(row), indent=2, default=str)

# --------- Tools

@mcp.tool()
def add_entry(topic: str, title: str, content: str, tags:str="", source:str="") -> str:
    """ADd a new entry to the knowledge base. Returns the new entry ID."""
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO entries (topic, title, content, tags, source) VALUES (?,?,?,?,?)",
            (topic, title, content, tags, source)
        )
        return f"ADded entry #{cur.lastrowid}: {title}"
    

@mcp.tool()
def search(query: str, topic: str = "", limit: int = 10) -> str:
    """
    Full-text search across all entries using FTS5.
    Optionally filter by topic.
    """
    with get_db() as conn:
        try:
            sql = """SELECT e.id, e.topic, e.title, e.tags
                     FROM entries e JOIN entries_fts f ON e.id = f.rowid
                     WHERE entries_fts MATCH ?"""
            params = [query]
            if topic:
                sql += " AND e.topic = ?"
                params.append(topic)
            sql += f" LIMIT {limit}"
            rows = conn.execute(sql, params).fetchall()
        except Exception:
            # FTS fallback to LIKE
            q = f"%{query}%"
            sql = "SELECT id, topic, title, tags FROM entries WHERE (title LIKE ? OR content LIKE ?)"
            params = [q, q]
            if topic:
                sql += " AND topic = ?"
                params.append(topic)
            rows = conn.execute(sql + f" LIMIT {limit}", params).fetchall()

    if not rows:
        return "No results found."
    return "\n".join(f"#{r['id']} [{r['topic']}] {r['title']} | {r['tags']}" for r in rows)

@mcp.tool()
def get_entry(entry_id: int) -> str:
    """Get a specific entry by its ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if not row:
        return f"Entry #{entry_id} not found."
    return json.dumps(dict(row), indent=2, default=str)

@mcp.tool()
def update_entry(entry_id: int, content: str = None, tags: str = None, topic: str = None) -> str:
    """Update an existing entry. Only provided fields are changed."""
    updates = {}
    if content is not None: updates["content"] = content
    if tags is not None: updates["tags"] = tags
    if topic is not None: updates["topic"] = topic
    if not updates:
        return "Nothing to update — provide at least one field."
    updates["updated"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with get_db() as conn:
        conn.execute(f"UPDATE entries SET {set_clause} WHERE id = ?",
                     list(updates.values()) + [entry_id])
    return f"Updated entry #{entry_id}"

@mcp.tool()
def delete_entry(entry_id: int) -> str:
    """Delete a knowledge base entry by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT title FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return f"Entry #{entry_id} not found."
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    return f"Deleted #{entry_id}: {row['title']}"

@mcp.tool()
def link_entries(from_id: int, to_id: int, relation: str) -> str:
    """
    Create a relationship link between two entries.
    relation examples: 'related_to', 'depends_on', 'contradicts', 'extends'
    """
    with get_db() as conn:
        for eid in (from_id, to_id):
            if not conn.execute("SELECT id FROM entries WHERE id = ?", (eid,)).fetchone():
                return f"Entry #{eid} not found."
        conn.execute("INSERT INTO links (from_id, to_id, relation) VALUES (?,?,?)",
                     (from_id, to_id, relation))
    return f"Linked #{from_id} —{relation}→ #{to_id}"

@mcp.tool()
def get_related(entry_id: int) -> str:
    """Get all entries linked to a given entry (both directions)."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT e.id, e.title, l.relation, 'outgoing' AS dir
            FROM links l JOIN entries e ON l.to_id = e.id WHERE l.from_id = ?
            UNION
            SELECT e.id, e.title, l.relation, 'incoming' AS dir
            FROM links l JOIN entries e ON l.from_id = e.id WHERE l.to_id = ?
        """, (entry_id, entry_id)).fetchall()
    if not rows:
        return f"No linked entries for #{entry_id}."
    return "\n".join(f"#{r['id']} {r['title']} [{r['relation']}] ({r['dir']})" for r in rows)

@mcp.tool()
def run_query(sql: str) -> str:
    """
    Run a read-only SQL query. Only SELECT statements are permitted.
    Use this for custom analysis and reporting.
    """
    sql_stripped = sql.strip().upper()
    if not sql_stripped.startswith("SELECT"):
        return "Only SELECT queries are permitted."
    try:
        with get_db() as conn:
            rows = conn.execute(sql).fetchall()
        if not rows:
            return "Query returned no results."
        return json.dumps([dict(r) for r in rows[:50]], indent=2, default=str)
    except sqlite3.Error as e:
        return f"SQL error: {e}"
    
@mcp.tool()
def stats() -> str:
    """Get statistics about the knowledge base."""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        topics = conn.execute("SELECT COUNT(DISTINCT topic) FROM entries").fetchone()[0]
        links = conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        newest = conn.execute("SELECT title, created FROM entries ORDER BY created DESC LIMIT 1").fetchone()
    result = f"Entries: {total}\nTopics: {topics}\nLinks: {links}"
    if newest:
        result += f"\nNewest: '{newest['title']}' at {newest['created']}"
    return result

if __name__ == "__main__":
    mcp.run()