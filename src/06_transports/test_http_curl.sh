#!/bin/bash
# Test weather_server.py over HTTP Streamable transport using curl.
#
# Start the server first in another terminal:
#   python weather_server.py --transport http --port 8081
#
# Then run this script:
#   bash test_http_curl.sh

BASE="http://localhost:8081"
HEADERS='-H "Content-Type: application/json" -H "Accept: application/json, text/event-stream"'

echo ""
echo "=== HTTP STREAMABLE TRANSPORT TEST ==="
echo "Server: $BASE"
echo ""

echo "--- Step 1: initialize ---"
curl -s -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
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
echo "--- Step 2: tools/list ---"
curl -s -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {}
  }'
echo ""

echo ""
echo "--- Step 3: tools/call — list_available_cities ---"
curl -s -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
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
echo "--- Step 4: tools/call — get_weather for Tokyo ---"
curl -s -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
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
echo "--- Step 5: tools/call — compare_weather London vs Paris ---"
curl -s -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 5,
    "method": "tools/call",
    "params": {
      "name": "compare_weather",
      "arguments": {"city1": "london", "city2": "paris"}
    }
  }'
echo ""

echo ""
echo "--- Step 6: resources/list ---"
curl -s -X POST "$BASE/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": 6,
    "method": "resources/list",
    "params": {}
  }'
echo ""

echo ""
echo "=== DONE ==="
