# use async def for tools that call external services - it keeps the server responsive
from fastmcp import FastMCP
import asyncio, httpx
from typing import Literal

mcp = FastMCP("async-demo")

@mcp.tool()
async def fetch_multiple_urls(urls: list[str]) -> str:
    """
    Fetch multiple URLs concurrently and return a summary.
    Much faster than fetching them one by one.
    """
    async def fetch_one(url: str) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, follow_redirects=True)
                return {
                    "url": url,
                    "status": resp.status_code,
                    "size": len(resp.text),
                    "ok": resp.status_code < 400
                }
        except Exception as e:
            return {"url": url, "error": str(e), "ok": False}

    results = await asyncio.gather(*[fetch_one(u) for u in urls[:10]])
    lines = []
    for r in results:
        if r.get("ok"):
            lines.append(f"✓ {r['url']} — {r['status']} ({r['size']} chars)")
        else:
            lines.append(f"✗ {r['url']} — {r.get('error', r.get('status'))}")
    return "\n".join(lines)

@mcp.tool()
async def run_concurrently(task_count: int = 5) -> str:
    """
    Simulate running multiple async tasks concurrently.
    Shows that async tools don't block each other.
    """
    async def task(i: int) -> str:
        await asyncio.sleep(0.1 * i)
        return f"Task {i} done"

    results = await asyncio.gather(*[task(i) for i in range(task_count)])
    return "\n".join(results)

if __name__ == "__main__":
    mcp.run()