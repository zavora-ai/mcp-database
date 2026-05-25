#!/bin/bash
# End-to-end test for mcp-database
# Starts the test backend, runs all 22 tools, reports results.
#
# Usage:
#   ./run_tests.sh
#
# Prerequisites:
#   - cargo build (in parent directory)
#   - python3

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BINARY="$PROJECT_DIR/target/debug/mcp-database"
PORT=7799

# Build if needed
if [ ! -f "$BINARY" ]; then
    echo "Building mcp-database..."
    cd "$PROJECT_DIR" && cargo build
fi

# Kill any existing server on the port
kill $(lsof -ti:$PORT) 2>/dev/null || true
sleep 1

# Start test backend
echo "Starting test backend on :$PORT..."
python3 "$SCRIPT_DIR/test_server.py" &
SERVER_PID=$!
sleep 1

# Verify server is up
if ! curl -s "http://localhost:$PORT/schema/tables" > /dev/null 2>&1; then
    echo "❌ Test server failed to start"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

echo "Running all 22 tools..."
echo ""

# Run all tools via MCP protocol
RESULT=$(printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_tables","arguments":{}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"describe_table","arguments":{"table":"users"}}}
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_relationships","arguments":{"table":"orders"}}}
{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"list_indexes","arguments":{"table":"users"}}}
{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"get_database_stats","arguments":{}}}
{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"search_schema","arguments":{"query":"email"}}}
{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"query","arguments":{"sql":"SELECT id, email, plan FROM users WHERE plan = $1","params":["enterprise"]}}}
{"jsonrpc":"2.0","id":9,"method":"tools/call","params":{"name":"sample_data","arguments":{"table":"users","limit":3}}}
{"jsonrpc":"2.0","id":10,"method":"tools/call","params":{"name":"filter_table","arguments":{"table":"users","limit":2}}}
{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"explain_query","arguments":{"sql":"SELECT * FROM users WHERE plan = '\''enterprise'\''"}}}
{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"get_column_stats","arguments":{"table":"users","schema":"plan"}}}
{"jsonrpc":"2.0","id":13,"method":"tools/call","params":{"name":"execute","arguments":{"sql":"UPDATE users SET email_verified = true WHERE id = $1","params":["u-001"]}}}
{"jsonrpc":"2.0","id":14,"method":"tools/call","params":{"name":"create_index","arguments":{"table":"orders","columns":["user_id","created_at"]}}}
{"jsonrpc":"2.0","id":15,"method":"tools/call","params":{"name":"run_migration","arguments":{"name":"add_phone_column","sql_up":"ALTER TABLE users ADD COLUMN phone VARCHAR(20)"}}}
{"jsonrpc":"2.0","id":16,"method":"tools/call","params":{"name":"list_migrations","arguments":{}}}
{"jsonrpc":"2.0","id":17,"method":"tools/call","params":{"name":"get_slow_queries","arguments":{}}}
{"jsonrpc":"2.0","id":18,"method":"tools/call","params":{"name":"get_connections","arguments":{}}}
{"jsonrpc":"2.0","id":19,"method":"tools/call","params":{"name":"get_maintenance_status","arguments":{}}}
{"jsonrpc":"2.0","id":20,"method":"tools/call","params":{"name":"get_index_usage","arguments":{}}}
{"jsonrpc":"2.0","id":21,"method":"tools/call","params":{"name":"generate_schema","arguments":{"query":"events table with id, name, payload, and timestamp"}}}
{"jsonrpc":"2.0","id":22,"method":"tools/call","params":{"name":"get_er_diagram","arguments":{}}}
{"jsonrpc":"2.0","id":23,"method":"tools/call","params":{"name":"validate_sql","arguments":{"sql":"SELECT * FROM users WHERE plan = '\''enterprise'\''"}}}
' | DATABASE_API_URL="http://127.0.0.1:$PORT" "$BINARY" 2>/dev/null | python3 -c "
import sys, json

names = {
    2: 'list_tables', 3: 'describe_table', 4: 'get_relationships',
    5: 'list_indexes', 6: 'get_database_stats', 7: 'search_schema',
    8: 'query', 9: 'sample_data', 10: 'filter_table',
    11: 'explain_query', 12: 'get_column_stats', 13: 'execute',
    14: 'create_index', 15: 'run_migration', 16: 'list_migrations',
    17: 'get_slow_queries', 18: 'get_connections', 19: 'get_maintenance_status',
    20: 'get_index_usage', 21: 'generate_schema', 22: 'get_er_diagram',
    23: 'validate_sql'
}

results = {}
for line in sys.stdin:
    line = line.strip()
    if not line.startswith('{'): continue
    r = json.loads(line)
    rid = r.get('id')
    if rid in names:
        if 'error' in r:
            results[rid] = ('❌', r['error']['message'][:50])
        else:
            text = r['result']['content'][0]['text']
            if 'Error' in text:
                results[rid] = ('❌', text[:50])
            else:
                results[rid] = ('✅', '')

passed = sum(1 for s, _ in results.values() if s == '✅')
failed = sum(1 for s, _ in results.values() if s == '❌')
total = len(names)

print(f'Results: {passed}/{total} passed, {failed} failed')
print()
for rid in sorted(names.keys()):
    if rid in results:
        status, msg = results[rid]
        extra = f' — {msg}' if msg else ''
        print(f'  {status} {names[rid]}{extra}')
    else:
        print(f'  ⚠️  {names[rid]} — no response')

print()
if passed == total:
    print('🎉 All tests passed!')
elif failed == 0:
    missing = total - passed
    print(f'⚠️  {missing} tools did not respond (may need more time)')
else:
    print(f'❌ {failed} tests failed')
")

echo "$RESULT"

# Cleanup
kill $SERVER_PID 2>/dev/null
echo ""
echo "Test backend stopped."
