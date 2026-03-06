# Chapter 14 — Testing

## Two Levels of Testing

1. **Unit tests** — test tool/resource functions directly, no subprocess, no MCP protocol
2. **Integration tests** — spawn the real server, test via the actual JSON-RPC protocol

Both are necessary. Unit tests are fast; integration tests catch protocol bugs.

## Unit Tests

```python
# chapter14/test_unit.py
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ─── Test utility server ───────────────────────────────────────────────────────

from chapter02.utility_server import calculate, hash_text, encode_decode, count_words

def test_calculate_basic():
    assert calculate("2 + 2") == "4"

def test_calculate_sqrt():
    assert calculate("sqrt(144)") == "12.0"

def test_calculate_power():
    assert calculate("2 ** 10") == "1024"

def test_calculate_invalid():
    result = calculate("import os; os.system('rm -rf /')")
    assert "Error" in result

def test_hash_text_sha256():
    result = hash_text("hello", "sha256")
    assert len(result) == 64
    assert result == hash_text("hello", "sha256")  # deterministic

def test_hash_text_invalid_algorithm():
    result = hash_text("hello", "md999")
    assert "Unsupported" in result

def test_encode_decode_roundtrip():
    original = "Hello, MCP!"
    encoded = encode_decode(original, "encode")
    decoded = encode_decode(encoded, "decode")
    assert decoded == original

def test_encode_decode_invalid_operation():
    result = encode_decode("text", "compress")
    assert "Unknown operation" in result

def test_count_words():
    result = count_words("Hello world. How are you?")
    assert isinstance(result, dict)
    assert result["words"] == 5
    assert result["sentences"] == 2

def test_count_words_empty():
    result = count_words("")
    assert result["words"] == 0

# ─── Test knowledge base ───────────────────────────────────────────────────────

import tempfile, json
from pathlib import Path

# Patch DB_FILE before importing to use a temp file
import chapter04.knowledge_base as kb_module
_original_db = kb_module.DB_FILE

@pytest.fixture(autouse=True)
def temp_db(tmp_path):
    kb_module.DB_FILE = tmp_path / "test_kb.json"
    yield
    kb_module.DB_FILE = _original_db

from chapter04.knowledge_base import add_entry, search, delete_entry

def test_add_and_search():
    add_entry("mcp", "Tools", "Tools are functions the LLM can call", "tools,functions")
    add_entry("mcp", "Resources", "Resources are data exposed for reading", "resources,data")
    result = search("LLM")
    assert "Tools" in result

def test_search_no_results():
    result = search("nonexistent_xyz_12345")
    assert "No results" in result

def test_delete_entry():
    add_entry("test", "To Delete", "This will be deleted")
    result = search("deleted")
    assert "To Delete" in result
    delete_entry("1")
    result2 = search("deleted")
    assert "To Delete" not in result2
```

## Integration Tests

```python
# chapter14/test_integration.py
"""
Spawn the real server and test via actual MCP protocol.
"""
import asyncio, json, pytest

class MCPTestClient:
    def __init__(self, script: str):
        self.script = script
        self.proc = None
        self._id = 0

    async def __aenter__(self):
        self.proc = await asyncio.create_subprocess_exec(
            "python", self.script,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await self._req("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0.0.0"}
        })
        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return self

    async def __aexit__(self, *_):
        self.proc.terminate()
        await self.proc.wait()

    async def _send(self, msg):
        self.proc.stdin.write((json.dumps(msg) + "\n").encode())
        await self.proc.stdin.drain()

    async def _req(self, method, params=None):
        self._id += 1
        await self._send({"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}})
        while True:
            line = await asyncio.wait_for(self.proc.stdout.readline(), timeout=10)
            r = json.loads(line)
            if r.get("id") == self._id:
                if "error" in r:
                    raise RuntimeError(str(r["error"]))
                return r.get("result", {})

    async def list_tools(self) -> list[dict]:
        return (await self._req("tools/list")).get("tools", [])

    async def call_tool(self, name: str, args: dict = None) -> dict:
        return await self._req("tools/call", {"name": name, "arguments": args or {}})

    async def list_resources(self) -> list[dict]:
        return (await self._req("resources/list")).get("resources", [])

@pytest.mark.asyncio
async def test_utility_server_tools_listed():
    async with MCPTestClient("chapter02/utility_server.py") as c:
        tools = await c.list_tools()
        names = {t["name"] for t in tools}
        assert "calculate" in names
        assert "hash_text" in names
        assert "encode_decode" in names
        assert "count_words" in names
        assert "timestamp" in names

@pytest.mark.asyncio
async def test_utility_server_calculate():
    async with MCPTestClient("chapter02/utility_server.py") as c:
        result = await c.call_tool("calculate", {"expression": "2 + 2"})
        assert result["content"][0]["text"] == "4"

@pytest.mark.asyncio
async def test_utility_server_hash():
    async with MCPTestClient("chapter02/utility_server.py") as c:
        result = await c.call_tool("hash_text", {"text": "hello", "algorithm": "sha256"})
        text = result["content"][0]["text"]
        assert len(text) == 64  # sha256 hex is 64 chars

@pytest.mark.asyncio
async def test_notes_server_create_and_read():
    import tempfile
    from pathlib import Path
    # Point notes server to temp dir via env
    import os
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["NOTES_DIR"] = tmp
        # Note: test_client would need env support — simplified here
        async with MCPTestClient("chapter04/notes_server.py") as c:
            # Create a note
            result = await c.call_tool("create_note",
                                       {"title": "Test Note", "content": "Test content"})
            assert "Created" in result["content"][0]["text"]

@pytest.mark.asyncio
async def test_protocol_version():
    """Server must respond to initialize with a valid protocol version."""
    import asyncio
    proc = await asyncio.create_subprocess_exec(
        "python", "chapter02/utility_server.py",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    msg = json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test", "version": "0.0.0"}
        }
    }) + "\n"
    proc.stdin.write(msg.encode())
    await proc.stdin.drain()
    line = await asyncio.wait_for(proc.stdout.readline(), timeout=5)
    resp = json.loads(line)
    assert "result" in resp
    assert "protocolVersion" in resp["result"]
    proc.terminate()
    await proc.wait()
```

## Run Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all unit tests
pytest chapter14/test_unit.py -v

# Run integration tests
pytest chapter14/test_integration.py -v

# Run everything
pytest chapter14/ -v --tb=short

# With coverage
pip install pytest-cov
pytest chapter14/ --cov=. --cov-report=term-missing
```

## pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = chapter14
python_files = test_*.py
python_functions = test_*
```
