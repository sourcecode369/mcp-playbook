from fastmcp import FastMCP

mcp = FastMCP("sse-demo")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    return f"pong: {message} via SSE"

@mcp.resource("status://health")
def health() -> str:
    """Server health status."""
    return '{"status": "ok", "transport": "sse"}'

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8080)