from fastmcp import FastMCP
from mcp.server.fastmcp import Context

mcp = FastMCP("dynamic-tools")

_enabled: set[str] = {"tool_a"}

@mcp.tool()
async def tool_a(ctx: Context) -> str:
    """Tool A - always available"""
    await ctx.info("Tool A executed")
    return "Tool A result"

@mcp.tool()
async def tool_b(ctx: Context) -> str:
    """Tool B - only available when enabled."""
    await ctx.info("Tool B executed")
    return "Tool B result"

@mcp.tool()
async def enable_tool(name: str, ctx: Context) -> str:
    _enabled.add(name)
    await ctx.info(f"Enabled: {name}")
    return f"Enabled tool: {name}. Reconnect to see it."

if __name__ == "__main__":
    mcp.run()