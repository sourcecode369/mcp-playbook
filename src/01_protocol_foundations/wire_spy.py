# chapter01/wire_spy.py
"""
Transparent proxy that logs all MCP messages to a file.
Use as a wrapper in Claude Desktop config instead of your server directly.

Claude Desktop config (claude_desktop_config.json):
{
  "mcpServers": {
    "hello-spied": {
      "command": "/absolute/path/to/.venv/bin/python3",
      "args": [
        "/absolute/path/to/src/01_protocol_foundations/wire_spy.py",
        "/absolute/path/to/.venv/bin/python3",
        "/absolute/path/to/src/00_setup/hello_server.py"
      ]
    }
  }
}

Watch the log:
  tail -f /tmp/mcp_wire.log
"""
import sys, json, threading, os

LOG = open("/tmp/mcp_wire.log", "w")
TARGET = sys.argv[1:]  # e.g. ["python", "my_server.py"]

import subprocess
proc = subprocess.Popen(
    TARGET,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

def pipe_with_log(src, dst, label):
    while True:
        line = src.readline()
        if not line: break
        try:
            msg = json.loads(line)
            LOG.write(f"[{label}] {json.dumps(msg)}\n")
            LOG.flush()
        except Exception:
            pass
        dst.write(line)
        dst.flush()

t1 = threading.Thread(target=pipe_with_log, args=(sys.stdin.buffer, proc.stdin, "IN "), daemon=True)
t2 = threading.Thread(target=pipe_with_log, args=(proc.stdout, sys.stdout.buffer, "OUT"), daemon=True)
t1.start(); t2.start()
proc.wait()