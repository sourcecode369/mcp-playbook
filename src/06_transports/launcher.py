import argparse
from fastmcp import FastMCP

mcp = FastMCP("multi-transport")

@mcp.tool()
def ping(message: str) -> str:
    """Ping the server"""
    return f"pong: {message}"

@mcp.resource("info://transport")
def transport_info() -> str:
    """Information about this server."""
    return '{"server": "multi-transport"}, "version":"1.0"'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=["stdio", "sse", "http"], default="stdio")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    
    if args.transport == "stdio": mcp.run() 
    else: mcp.run(transport=args.transport, host=args.host, port=args.port) 