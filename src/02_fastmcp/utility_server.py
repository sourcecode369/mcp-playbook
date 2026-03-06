from fastmcp import FastMCP
import math, hashlib, base64, re
from datetime import datetime

mcp = FastMCP("utilities")

@mcp.tool()
def calculate(expression: str) -> str:
    """
    Evaluate a safe mathematical expression.
    Supports: +, -, *, /, **, sqrt, log, sin, cos, pi, e
    Example: "sqrt(144) + 2**8"
    """
    allowed = {
        k: getattr(math, k) for k in dir(math) if not k.startswith("_")
    }
    allowed.update({"abs": abs, "round": round})
    try:
        result = eval(expression, {"__builtins__": {}}, allowed)
        return str(result)
    except Exception as e:
        return f"Error: {e}"
    
@mcp.tool()
def hash_text(text: str, algorithm: str = "sha256") -> str:
    """
        Hash a string using md5, sha1, sha256 or sha512.
        Returns the hex digest.
    """
    
    if algorithm not in ("md5", "sha1", "sha256", "sha512"):
        return f"Unsupported algorithm: {algorithm}"
    h = hashlib.new(algorithm)
    h.update(text.encode())
    return h.hexdigest()

@mcp.tool()
def encode_decode(text: str, operation: str="encode") -> str:
    """
        Base64 encode or decode a string.
        Operation must be 'encode' or 'decode'.
    """
    
    if operation == "encode":
        return base64.b64encode(text.encode()).decode()
    elif operation == "decode":
        try:
            return base64.b64decode(text.encode()).decode()
        except Exception as e:
            return f"Decode error: {e}"
    
    return f"Unknown operation: {operation}"

@mcp.tool()
def count_words(text: str) -> dict:
    """
        Count words, characters, sentences, and unique words in text.
        Returns a dict with counts.
    """
    
    words = text.split()
    sentences = re.split(r'[.!?]+', text)
    sentences = [s for s in sentences if s.strip()]
    return {
        'words': len(words),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "sentences": len(sentences),
        "unique_words": len(set(w.lower().strip(".,!?") for w in words))
    }
    
@mcp.tool()
def timestamp(
    format: str = "iso",
    timezone: str = "utc"
) -> str:
    """
        Get current timestamp. 
        Format options: iso, unix, human, date, time
        timezone: utc or local
    """
    
    from datetime import timezone as tz
    now_utc = datetime.now(tz.utc)
    now = now_utc if timezone == "utc" else datetime.now()
    
    formats = {
        "iso": now.isoformat(),
        "unix": str(int(now.timestamp())),
        "human": now.strftime("%B %d, %Y at %I:%M %p"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%$"),
    }
    
    return formats.get(format, now.isoformat())

if __name__ == "__main__":
    mcp.run()