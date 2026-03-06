import asyncio, json, subprocess, sys

async def explore():
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-c", """
from fastmcp import FastMCP
mcp = FastMCP("demo")

@mcp.tool()
def add(a: int, b: int) -> int:
    \"\"\"Add two numbers.\"\"\"
    return a + b

mcp.run()
""",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def send(msg):
        raw = json.dumps(msg) + "\n"
        print(f"\n>>> {json.dumps(msg, indent=2)}")
        proc.stdin.write(raw.encode())
        await proc.stdin.drain()

    async def recv():
        line = await proc.stdout.readline()
        if not line:
            err = await proc.stderr.read()
            raise RuntimeError(f"Server produced no output. stderr:\n{err.decode()}")
        msg = json.loads(line)
        print(f"\n<<< {json.dumps(msg, indent=2)}")
        return msg

    # Step 1: initialize handshake
    await send({
        "jsonrpc": "2.0", "id": 1, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}},
            "clientInfo": {"name": "explorer", "version": "0.1.0"}
        }
    })
    await recv()

    # Step 2: initialized notification
    await send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    # Step 3: list tools
    await send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    await recv()

    # Step 4: call a tool
    await send({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "add", "arguments": {"a": 10, "b": 32}}
    })
    await recv()

    proc.terminate()
    print("\n\nDone — you just spoke raw MCP protocol.")

asyncio.run(explore())