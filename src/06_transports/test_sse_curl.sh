#!/bin/bash
# Test weather_server.py over SSE transport using curl.
#
# Start the server first in another terminal:
#   python weather_server.py --transport sse --port 8080
#
# Then run this script:
#   bash test_sse_curl.sh

BASE="http://localhost:8080"

echo ""
echo "=== SSE TRANSPORT TEST ==="
echo "Server: $BASE"
echo ""

# SSE uses two endpoints:
#   GET  /sse        — open the event stream (keep-alive, responses come here)
#   POST /messages/  — send requests here
#
# curl can't fully test SSE (it's a streaming protocol meant for long-lived connections).
# Instead we POST to /messages/ directly to verify the server is alive and responding.
# For full SSE testing use the MCP Inspector or the Python client in Chapter 11.

echo "--- Step 1: Verify server is reachable ---"
curl -s -o /dev/null -w "HTTP status: %{http_code}\n" "$BASE/sse"

echo ""
echo "--- Step 2: POST initialize to /messages/ ---"
curl -s -X POST "$BASE/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "curl-test", "version": "0.1"}
    }
  }'
echo ""

echo ""
echo "--- Step 3: POST tools/list ---"
curl -s -X POST "$BASE/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
echo ""

echo ""
echo "--- Step 4: POST tools/call (list_available_cities) ---"
curl -s -X POST "$BASE/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "list_available_cities",
      "arguments": {}
    }
  }'
echo ""

echo ""
echo "--- Step 5: POST tools/call (get_weather for Tokyo) ---"
curl -s -X POST "$BASE/messages/" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 4,
    "method": "tools/call",
    "params": {
      "name": "get_weather",
      "arguments": {"city": "tokyo"}
    }
  }'
echo ""

echo ""
echo "=== NOTE ==="
echo "SSE responses arrive on the GET /sse stream, not as POST responses."
echo "The POSTs above return 202 Accepted — actual JSON-RPC responses"
echo "stream back on the open GET /sse connection."
echo "Use the MCP Inspector or Python client (Chapter 11) for full SSE testing."
