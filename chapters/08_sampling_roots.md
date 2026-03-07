# Chapter 8 — Sampling & Roots

## Sampling — Server-Initiated LLM Calls

Every chapter so far has followed one direction: the client (Claude) decides to call a tool, the server executes it, returns a result. Sampling flips this.

Sampling lets the **server** ask the **client's LLM** to generate a completion mid-execution. The server sends a `sampling/createMessage` request, the client's LLM generates a response, and the result is returned to the server — all without the user seeing it happen.

```
Normal flow:
  User message → Claude → decides to call tool → server executes → result returned

Sampling flow:
  User message → Claude → calls tool → server runs → server asks LLM a question
                                                              ↓
                                                       LLM generates answer
                                                              ↓
                                                    server continues with that answer
                                                              ↓
                                                       result returned to Claude
```

This is what makes MCP servers genuinely intelligent — they're not just wrappers around functions. They can reason, evaluate, and make decisions using the same LLM the user is talking to.

## Why Sampling Exists

Without sampling, a server can only return raw data. With sampling, a server can return *intelligence*:

| Without Sampling | With Sampling |
|---|---|
| Return 5000 chars of file content | Return a 3-sentence summary of the file |
| Return raw JSON from an API | Return an interpretation of what the data means |
| Return a list of search results | Return the most relevant result with an explanation |
| Return a diff | Return what the change actually does |

The server becomes an agent layer, not just a data layer.

## How Sampling Works (Protocol Level)

```
Client (Claude Desktop)              Server (your FastMCP server)
        │                                       │
        │── tools/call ────────────────────────►│
        │                                       │ (server starts executing)
        │◄── sampling/createMessage ────────────│ (server asks LLM)
        │ (Claude generates a completion)        │
        │── sampling result ───────────────────►│ (server gets the answer)
        │                                       │ (server continues)
        │◄── tools/call result ─────────────────│ (final result to user)
```

The sampling request contains messages (what to ask), an optional system prompt, and token limits. The client uses its LLM to generate a completion and returns it synchronously.

## Important: Client Must Support Sampling

Sampling is a **capability** that must be declared during the `initialize` handshake:

```json
// Client declares it supports sampling
{
  "capabilities": {
    "sampling": {}
  }
}
```

**Claude Desktop supports sampling.** If you use a custom client (Chapter 11), you must implement the `sampling/createMessage` handler yourself, otherwise `ctx.sample()` calls will fail.

## When to Use Sampling

- Summarize a large file before returning it
- Classify or route user intent inside the server
- Generate structured output from raw data
- Make intelligent decisions inside a multi-step tool
- Evaluate quality of data before returning it
- Generate a natural language explanation of technical output

## Sampling with FastMCP

```python
from fastmcp import FastMCP
from mcp.server.fastmcp import Context

mcp = FastMCP("sampling-demo")

@mcp.tool()
async def smart_summarize(path: str, max_words: int = 100, ctx: Context) -> str:
    """Read a file and return an AI-generated summary using sampling."""
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"

    content = p.read_text(encoding="utf-8", errors="replace")[:8000]

    # Ask the client's LLM to summarize
    result = await ctx.sample(
        f"Summarize the following content in at most {max_words} words. "
        f"Return only the summary, no preamble.\n\n{content}",
        system_prompt="You are a concise technical summarizer."
    )
    return result.text
```

## Roots — Filesystem Boundaries

### What Are Roots?

Roots are a security mechanism. When a client connects to a server, it can declare which filesystem paths it's willing to let the server access. The server then calls `roots/list` to discover these declared boundaries and should respect them.

```
Client declares:  "You may access /home/user/project and /home/user/documents"
Server asks:      roots/list
Client responds:  [{uri: "file:///home/user/project", name: "My Project"},
                   {uri: "file:///home/user/documents", name: "Documents"}]
Server respects:  Only reads/writes within those paths
```

This is a **trust contract**, not enforced at the protocol level. The server voluntarily respects roots. It's your responsibility as the server author to check roots before accessing the filesystem.

### Why Roots Exist

Without roots, a server connected to Claude Desktop could theoretically access any file on your machine. Roots let the client say: *"I'm allowing you to connect, but only touch these specific directories."*

In practice, Claude Desktop lets you configure roots per server in the config. A document editing server might be given `~/Documents` as its root. A coding server might be given `~/projects`.

### Roots vs. Your Own Path Validation

Roots are what the client tells you. You still need your own path validation (Chapter 13 — Security) to prevent path traversal attacks (`../../etc/passwd` style). Roots narrow the scope; your code enforces it.

Roots are URI prefixes the client declares the server is allowed to access. The server calls `list_roots()` to discover them:

```python
@mcp.tool()
async def list_allowed_roots(ctx: Context) -> str:
    """List filesystem roots that the client has declared accessible."""
    roots = await ctx.list_roots()
    if not roots:
        return "No roots declared by client."
    return "\n".join(f"{r.name}: {r.uri}" for r in roots)
```

---

## Project 8: Sampling-Powered Smart Server

```python
# chapter08/sampling_server.py
from fastmcp import FastMCP
from mcp.server.fastmcp import Context
from pathlib import Path
import json

mcp = FastMCP("smart-tools")

@mcp.tool()
async def smart_read(path: str, ctx: Context) -> str:
    """
    Read a file and return an AI-generated summary with key insights.
    Uses sampling to ask the LLM to analyze the content.
    """
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"

    content = p.read_text(encoding="utf-8", errors="replace")
    await ctx.info(f"Read {len(content)} chars from {path}")

    if len(content) < 500:
        # Short file — return as-is
        return content

    # Use sampling to summarize
    result = await ctx.sample(
        f"Analyze this file and provide:\n"
        f"1. A 2-sentence summary\n"
        f"2. The 3 most important points\n"
        f"3. The file type/purpose\n\n"
        f"File content:\n{content[:6000]}",
        system_prompt="You are a concise technical analyst. Be brief."
    )
    return f"FILE: {path}\nSIZE: {len(content)} chars\n\nANALYSIS:\n{result.text}"

@mcp.tool()
async def classify_file(path: str, ctx: Context) -> str:
    """
    Classify a file's content type and purpose using sampling.
    Returns: type, language (if code), confidence, and a one-line description.
    """
    p = Path(path)
    if not p.exists():
        return f"File not found: {path}"

    content = p.read_text(encoding="utf-8", errors="replace")[:3000]

    result = await ctx.sample(
        f"Classify this file. Respond with ONLY valid JSON:\n"
        f'{{"type": "code|documentation|data|config|prose|other", '
        f'"language": "python|javascript|null etc", '
        f'"confidence": 0.0-1.0, '
        f'"description": "one line"}}\n\n'
        f"Content:\n{content}",
        system_prompt="Respond with only valid JSON, no explanation."
    )

    try:
        classification = json.loads(result.text)
        return json.dumps(classification, indent=2)
    except json.JSONDecodeError:
        return result.text

@mcp.tool()
async def smart_compare(path1: str, path2: str, ctx: Context) -> str:
    """
    Compare two files and describe the key differences using sampling.
    """
    p1, p2 = Path(path1), Path(path2)
    for p in (p1, p2):
        if not p.exists():
            return f"File not found: {p}"

    c1 = p1.read_text(encoding="utf-8", errors="replace")[:3000]
    c2 = p2.read_text(encoding="utf-8", errors="replace")[:3000]

    result = await ctx.sample(
        f"Compare these two files and describe the key differences.\n\n"
        f"FILE 1 ({path1}):\n{c1}\n\n"
        f"FILE 2 ({path2}):\n{c2}\n\n"
        f"Focus on: purpose, structure, content differences. Be concise.",
        system_prompt="You are a code and document comparison tool."
    )
    return result.text

@mcp.tool()
async def roots_info(ctx: Context) -> str:
    """Show filesystem roots declared accessible by the client."""
    try:
        roots = await ctx.list_roots()
        if not roots:
            return "No roots declared. The client hasn't specified allowed filesystem paths."
        lines = [f"Accessible roots ({len(roots)}):"]
        for r in roots:
            lines.append(f"  {r.name or '(unnamed)'}: {r.uri}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not retrieve roots: {e}"

if __name__ == "__main__":
    mcp.run()
```

**Test in Claude Desktop:**
- *"Read and summarize my README.md file"* — observe that sampling kicks in for large files
- *"Classify the files in my project"* — Claude calls classify_file multiple times
- *"What filesystem paths are you allowed to access?"*

**Note on sampling availability:** Sampling requires the client to support it. Claude Desktop supports sampling. When testing via the raw Claude API (custom client), you'll need to implement the sampling handler in your client.
