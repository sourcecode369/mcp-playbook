# Chapter 8 — Sampling & Roots

## Sampling — Server-Initiated LLM Calls

Sampling lets the **server** ask the **client's LLM** to generate a completion. The flow:

```
Normal:   Client(LLM) ──calls──► Server(tool)
Sampling: Server ──sampling/createMessage──► Client ──► LLM ──► Server
```

This enables agentic server-side behavior. A server can reason, summarize, classify, or make decisions using the LLM without the user needing to ask explicitly.

## When to Use Sampling

- Summarize a large file before returning it
- Classify or route user intent inside the server
- Generate structured output from raw data
- Make intelligent decisions inside a multi-step tool

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
