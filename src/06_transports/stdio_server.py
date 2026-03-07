from fastmcp import FastMCP
import sys

mcp = FastMCP("stdio-demo")

@mcp.tool()
def ping(message: str = "hello") -> str:
    """Ping the server."""
    print("debug output goes here", file=sys.stderr)  # CORRECT
    # print("this breaks everything")                  # WRONG
    return f"pong: {message} via stdio"

if __name__ == "__main__":
    mcp.run()  # default transport is stdio