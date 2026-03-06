from fastmcp import FastMCP

mcp = FastMCP("hello")

@mcp.tool()
def hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}! MCP is working."

if __name__ == "__main__":
    mcp.run()