from fastmcp import FastMCP

mcp = FastMCP("http-demo")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    return f"pong: {message} via HTTP Streamable"

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8081)