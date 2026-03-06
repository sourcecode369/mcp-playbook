from fastmcp import FastMCP

mcp = FastMCP("my-first-server")

@mcp.tool()
def add(a: int, b:int) -> int:
    """Add two number together"""
    return a+b

@mcp.tool()
def greet(name: str, formal: bool = False) -> str:
    """Greet a person. Set formal=True for professional greeting."""
    if formal:
        return F"Good day, {name}."
    return f"Hey {name}!"

if __name__ == "__main__":
    mcp.run()