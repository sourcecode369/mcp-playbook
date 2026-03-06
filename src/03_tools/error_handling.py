from fastmcp import FastMCP
import httpx, json
from typing import Literal

mcp = FastMCP("error-patterns")

@mcp.tool()
def safe_divide(a: float, b: float) -> str:
    """
        Divide a by b. Returns an error message if b is zero
        instead of crashing, so the LLM can recover gracefully.
    """
    if b == 0:
        return "Cannot divide by zero. Please provide a non-zero divisor."
    return str( a / b )

@mcp.tool()
def fetch_url(url: str) -> str:
    """
        Fetch the content of a URL. Returns an error with details
        if the request fails, so the LLM knows what went wrong.
    """
    if not url.startswith(("https://", "http://")):
        return f"Invalid URL. Must start with https:// or http://"
    try:
        resp = httpx.get(url, timeout=0, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text[:5000]
        if len(resp.text) > 5000:
            text += f"\n\n [Truncated - {len(resp.text)} total chars]"
        return text
    except httpx.TimeoutException:
        return f"Request timed out after 10 seconds: {url}"
    except httpx.HTTPStatusError as e:
        return f"HTTP {e.response.status_code} error for {url}"
    except Exception as e:
        return f"Request failed {type(e).__name__}: {e}"
    
@mcp.tool()
def parse_json(text: str) -> str:
    """
        Parse and pretty-print a JSON string.
        Returns a helpful error message if the JSON is invalid.
    """
    try:
        parsed = json.loads(text)
        return json.dumps(parsed, indent=2)
    except json.JSONDecodeError as e:
        return f"Invalid JSON at position {e.pos}: {e.msg}\nInput was: {text[:200]}"
    
if __name__ == "__main__":
    mcp.run()