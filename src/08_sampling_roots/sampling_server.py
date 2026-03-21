from fastmcp import FastMCP
from fastmcp.server.context import Context
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
        return content

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
    Returns: type, language, confidence, and a one-line description.
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
        system_prompt="Respond with only valid JSON, no explanation.",
        max_tokens=200
    )

    try:
        return json.dumps(json.loads(result.text), indent=2)
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
    roots = await ctx.list_roots()
    if not roots:
        return "No roots declared. The client hasn't specified allowed filesystem paths."
    lines = [f"Accessible roots ({len(roots)}):"]
    for r in roots:
        lines.append(f"  {r.name or '(unnamed)'}: {r.uri}")
    return "\n".join(lines)

if __name__ == "__main__":
    mcp.run()
