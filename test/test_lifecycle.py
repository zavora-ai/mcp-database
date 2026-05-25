#!/usr/bin/env python3
"""
Full lifecycle test for mcp-database with real SQLite.
Sends MCP requests sequentially (waits for each response).

Usage:
    # Start backend first: python3 test_sqlite_backend.py
    # Then: python3 test_lifecycle.py
"""

import subprocess, json, sys, os

BINARY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "target", "debug", "mcp-database")
API_URL = "http://127.0.0.1:7799"

def call_tool(proc, tool_id, name, arguments):
    msg = json.dumps({"jsonrpc": "2.0", "id": tool_id, "method": "tools/call", "params": {"name": name, "arguments": arguments}}) + "\n"
    proc.stdin.write(msg.encode())
    proc.stdin.flush()

    # Read until we get our response
    while True:
        line = proc.stdout.readline().decode().strip()
        if not line:
            continue
        try:
            r = json.loads(line)
            if r.get("id") == tool_id:
                if "error" in r:
                    return None, r["error"]["message"]
                text = r["result"]["content"][0]["text"]
                try:
                    return json.loads(text), None
                except:
                    return text, None
        except:
            continue

def main():
    env = os.environ.copy()
    env["DATABASE_API_URL"] = API_URL

    proc = subprocess.Popen(
        [BINARY],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=env
    )

    # Initialize
    init_msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}) + "\n"
    proc.stdin.write(init_msg.encode())
    proc.stdin.flush()
    # Read init response
    while True:
        line = proc.stdout.readline().decode().strip()
        if '"id":1' in line or '"id": 1' in line:
            break

    print("═══════════════════════════════════════════════════════════")
    print("  mcp-database + SQLite — Full Lifecycle Test")
    print("═══════════════════════════════════════════════════════════")
    print()

    steps = [
        ("run_migration", {"name": "001_create_users", "sql_up": "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, name TEXT, plan TEXT DEFAULT 'free', created_at TEXT DEFAULT (datetime('now')))"}),
        ("run_migration", {"name": "002_create_orders", "sql_up": "CREATE TABLE orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER REFERENCES users(id), product TEXT NOT NULL, amount_cents INTEGER NOT NULL, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT (datetime('now')))"}),
        ("execute", {"sql": "INSERT INTO users (email, name, plan) VALUES ('alice@acme.com', 'Alice Chen', 'enterprise')"}),
        ("execute", {"sql": "INSERT INTO users (email, name, plan) VALUES ('bob@startup.io', 'Bob Smith', 'pro')"}),
        ("execute", {"sql": "INSERT INTO users (email, name, plan) VALUES ('carol@bigcorp.com', 'Carol Davis', 'enterprise')"}),
        ("execute", {"sql": "INSERT INTO orders (user_id, product, amount_cents, status) VALUES (1, 'Pro Plan', 4900, 'completed')"}),
        ("execute", {"sql": "INSERT INTO orders (user_id, product, amount_cents, status) VALUES (1, 'Enterprise Addon', 9900, 'pending')"}),
        ("execute", {"sql": "INSERT INTO orders (user_id, product, amount_cents, status) VALUES (2, 'Pro Plan', 4900, 'completed')"}),
        ("list_tables", {}),
        ("describe_table", {"table": "users"}),
        ("get_relationships", {"table": "orders"}),
        ("query", {"sql": "SELECT u.name, u.plan, COUNT(o.id) as order_count, SUM(o.amount_cents) as total_cents FROM users u LEFT JOIN orders o ON o.user_id = u.id GROUP BY u.id"}),
        ("query", {"sql": "SELECT * FROM orders WHERE status = 'completed'"}),
        ("create_index", {"table": "orders", "columns": ["user_id"]}),
        ("explain_query", {"sql": "SELECT * FROM orders WHERE user_id = 1"}),
        ("get_column_stats", {"table": "users", "schema": "plan"}),
        ("get_database_stats", {}),
        ("get_er_diagram", {}),
        ("sample_data", {"table": "users"}),
        ("list_migrations", {}),
        ("execute", {"sql": "DROP TABLE orders"}),
        ("execute", {"sql": "DROP TABLE users"}),
        ("list_tables", {}),
    ]

    labels = [
        "📦 CREATE TABLE users",
        "📦 CREATE TABLE orders (FK → users)",
        "➕ INSERT Alice (enterprise)",
        "➕ INSERT Bob (pro)",
        "➕ INSERT Carol (enterprise)",
        "➕ INSERT order: Alice → Pro Plan $49",
        "➕ INSERT order: Alice → Enterprise Addon $99",
        "➕ INSERT order: Bob → Pro Plan $49",
        "📋 LIST TABLES",
        "🔍 DESCRIBE users",
        "🔗 GET RELATIONSHIPS (orders → users)",
        "📊 QUERY: revenue per user (JOIN + GROUP BY)",
        "📊 QUERY: completed orders",
        "⚡ CREATE INDEX orders(user_id)",
        "📈 EXPLAIN QUERY PLAN",
        "📊 COLUMN STATS: users.plan",
        "💾 DATABASE STATS",
        "🗺️  ER DIAGRAM",
        "👀 SAMPLE DATA: users",
        "📜 MIGRATION HISTORY",
        "🗑️  DROP TABLE orders",
        "🗑️  DROP TABLE users",
        "📋 VERIFY TABLES DROPPED",
    ]

    passed = 0
    failed = 0

    for i, ((tool, args), label) in enumerate(zip(steps, labels)):
        data, err = call_tool(proc, i + 10, tool, args)
        if err:
            print(f"  ❌ {label}")
            print(f"     {err[:70]}")
            failed += 1
        elif isinstance(data, dict) and "error" in data:
            print(f"  ❌ {label}")
            print(f"     {data['error'][:70]}")
            failed += 1
        else:
            passed += 1
            # Pretty print result
            if isinstance(data, dict):
                if "applied" in data:
                    print(f"  ✅ {label} ({data.get('duration_ms','?')}ms)")
                elif "affected_rows" in data:
                    print(f"  ✅ {label} → {data['affected_rows']} row(s)")
                elif "created" in data:
                    print(f"  ✅ {label} → {data.get('index_name','')}")
                elif "columns" in data and "rows" in data:
                    print(f"  ✅ {label} → {data.get('row_count', len(data['rows']))} rows")
                    for row in data.get("rows", [])[:3]:
                        if isinstance(row, dict):
                            print(f"     {row}")
                        else:
                            print(f"     {row}")
                elif "table" in data and "columns" in data:
                    cols = ", ".join(c["name"] + " " + c["type"] for c in data["columns"])
                    print(f"  ✅ {label} → ({cols})")
                elif "plan" in data:
                    print(f"  ✅ {label}")
                    for p in data["plan"][:2]:
                        print(f"     {p}")
                elif "tables" in data and "relationships" in data:
                    print(f"  ✅ {label} → {len(data['tables'])} tables, {len(data['relationships'])} rels")
                elif "tables" in data:
                    print(f"  ✅ {label} → {data.get('total_rows', '?')} rows across {len(data['tables'])} tables")
                elif "distinct_count" in data:
                    vals = ", ".join(f"{v['value']}={v['count']}" for v in data.get("values", []))
                    print(f"  ✅ {label} → {vals}")
                elif "rows" in data:
                    print(f"  ✅ {label} → {len(data['rows'])} rows")
                else:
                    print(f"  ✅ {label}")
            elif isinstance(data, list):
                names = ", ".join(d.get("name", str(d)[:20]) for d in data[:5]) if data and isinstance(data[0], dict) else str(len(data))
                print(f"  ✅ {label} → [{names}]")
            else:
                print(f"  ✅ {label}")

    proc.terminate()
    print()
    print(f"  Results: {passed}/{passed+failed} passed, {failed} failed")
    if failed == 0:
        print("  🎉 Full lifecycle complete!")
    print()
    print("═══════════════════════════════════════════════════════════")

if __name__ == "__main__":
    main()
