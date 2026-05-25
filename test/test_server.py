"""
Test backend for mcp-database.
Simulates a database API with sample PostgreSQL-like responses.

Usage:
    python3 test_server.py
    # Runs on http://localhost:7799
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

TABLES = [
    {"name": "users", "schema": "public", "row_count": 48500, "size_mb": 12.4},
    {"name": "orders", "schema": "public", "row_count": 125000, "size_mb": 45.2},
    {"name": "products", "schema": "public", "row_count": 3200, "size_mb": 2.1},
    {"name": "sessions", "schema": "public", "row_count": 890000, "size_mb": 120.5},
]

USERS_SCHEMA = {
    "table": "users",
    "schema": "public",
    "row_count": 48500,
    "columns": [
        {"name": "id", "type": "uuid", "nullable": False, "primary_key": True},
        {"name": "email", "type": "varchar(255)", "nullable": False, "unique": True},
        {"name": "name", "type": "varchar(100)", "nullable": True},
        {"name": "plan", "type": "varchar(20)", "nullable": False, "default": "'free'"},
        {"name": "created_at", "type": "timestamptz", "nullable": False, "default": "now()"},
        {"name": "email_verified", "type": "boolean", "nullable": False, "default": "false"},
    ],
    "indexes": [
        {"name": "users_pkey", "columns": ["id"], "unique": True},
        {"name": "users_email_idx", "columns": ["email"], "unique": True},
        {"name": "users_plan_idx", "columns": ["plan"], "unique": False},
    ],
}

ORDERS_SCHEMA = {
    "table": "orders",
    "schema": "public",
    "row_count": 125000,
    "columns": [
        {"name": "id", "type": "uuid", "nullable": False, "primary_key": True},
        {"name": "user_id", "type": "uuid", "nullable": False, "references": "users.id"},
        {"name": "product_id", "type": "uuid", "nullable": False, "references": "products.id"},
        {"name": "amount_cents", "type": "integer", "nullable": False},
        {"name": "status", "type": "varchar(20)", "nullable": False, "default": "'pending'"},
        {"name": "created_at", "type": "timestamptz", "nullable": False, "default": "now()"},
    ],
    "indexes": [
        {"name": "orders_pkey", "columns": ["id"], "unique": True},
        {"name": "orders_user_id_idx", "columns": ["user_id"], "unique": False},
        {"name": "orders_created_at_idx", "columns": ["created_at"], "unique": False},
    ],
}

SAMPLE_USERS = [
    {"id": "u-001", "email": "alice@acme.com", "name": "Alice Chen", "plan": "enterprise", "created_at": "2023-03-15T10:00:00Z", "email_verified": True},
    {"id": "u-002", "email": "bob@startup.io", "name": "Bob Smith", "plan": "pro", "created_at": "2024-01-10T14:30:00Z", "email_verified": True},
    {"id": "u-003", "email": "carol@bigcorp.com", "name": "Carol Davis", "plan": "enterprise", "created_at": "2022-06-01T09:00:00Z", "email_verified": True},
    {"id": "u-004", "email": "dan@freelance.dev", "name": "Dan Lee", "plan": "free", "created_at": "2025-11-20T16:00:00Z", "email_verified": False},
    {"id": "u-005", "email": "eve@midsize.co", "name": "Eve Johnson", "plan": "pro", "created_at": "2024-08-05T11:00:00Z", "email_verified": True},
]

SAMPLE_ORDERS = [
    {"id": "o-001", "user_id": "u-001", "product_id": "p-001", "amount_cents": 9900, "status": "completed", "created_at": "2026-05-20T10:00:00Z"},
    {"id": "o-002", "user_id": "u-002", "product_id": "p-002", "amount_cents": 4900, "status": "completed", "created_at": "2026-05-22T14:00:00Z"},
    {"id": "o-003", "user_id": "u-001", "product_id": "p-003", "amount_cents": 19900, "status": "pending", "created_at": "2026-05-25T08:00:00Z"},
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        query_params = {}
        if "?" in self.path:
            for param in self.path.split("?")[1].split("&"):
                if "=" in param:
                    k, v = param.split("=", 1)
                    query_params[k] = v

        if path == "/schema/tables":
            data = TABLES
        elif path == "/schema/tables/users":
            data = USERS_SCHEMA
        elif path == "/schema/tables/orders":
            data = ORDERS_SCHEMA
        elif path.endswith("/relationships"):
            table = path.split("/")[3]
            if table == "orders":
                data = [
                    {"from_table": "orders", "from_column": "user_id", "to_table": "users", "to_column": "id", "type": "many_to_one"},
                    {"from_table": "orders", "from_column": "product_id", "to_table": "products", "to_column": "id", "type": "many_to_one"},
                ]
            else:
                data = [{"from_table": "orders", "from_column": "user_id", "to_table": "users", "to_column": "id", "type": "many_to_one"}]
        elif path.endswith("/indexes"):
            table = path.split("/")[3]
            data = USERS_SCHEMA["indexes"] if table == "users" else ORDERS_SCHEMA["indexes"]
        elif path == "/schema/stats":
            data = {"database_size_mb": 180.2, "tables": TABLES, "total_rows": 1066700, "index_count": 9}
        elif path == "/schema/search":
            q = query_params.get("q", "").lower()
            results = []
            for t in [USERS_SCHEMA, ORDERS_SCHEMA]:
                for col in t["columns"]:
                    if q in col["name"].lower() or q in t["table"].lower():
                        results.append({"table": t["table"], "column": col["name"], "type": col["type"]})
            data = results
        elif path == "/schema/er-diagram":
            data = {
                "tables": ["users", "orders", "products", "sessions"],
                "relationships": [
                    {"from": "orders.user_id", "to": "users.id", "type": "many_to_one"},
                    {"from": "orders.product_id", "to": "products.id", "type": "many_to_one"},
                    {"from": "sessions.user_id", "to": "users.id", "type": "many_to_one"},
                ],
            }
        elif "/sample" in path:
            table = path.split("/")[2]
            limit = int(query_params.get("limit", "5"))
            data = SAMPLE_USERS[:limit] if table == "users" else SAMPLE_ORDERS[:limit]
        elif "/columns/" in path and "/stats" in path:
            data = {
                "column": "plan",
                "distinct_count": 3,
                "null_count": 0,
                "values": [
                    {"value": "free", "count": 28400, "percentage": 58.6},
                    {"value": "pro", "count": 12000, "percentage": 24.7},
                    {"value": "enterprise", "count": 8100, "percentage": 16.7},
                ],
            }
        elif path == "/performance/slow-queries":
            data = [
                {"query": "SELECT * FROM orders WHERE created_at > $1 ORDER BY created_at DESC", "avg_ms": 2400, "calls": 150, "rows_returned": 45000},
                {"query": "SELECT COUNT(*) FROM sessions GROUP BY user_id HAVING COUNT(*) > 100", "avg_ms": 1800, "calls": 50, "rows_returned": 1200},
                {"query": "SELECT u.*, COUNT(o.id) FROM users u LEFT JOIN orders o ON o.user_id = u.id GROUP BY u.id", "avg_ms": 950, "calls": 300, "rows_returned": 48500},
            ]
        elif path == "/performance/connections":
            data = {
                "active": 12,
                "idle": 38,
                "max": 100,
                "utilization_pct": 50,
                "running_queries": [
                    {"pid": 1234, "query": "SELECT * FROM orders WHERE...", "duration_ms": 450, "state": "active"},
                    {"pid": 1235, "query": "INSERT INTO sessions...", "duration_ms": 12, "state": "active"},
                ],
            }
        elif path == "/performance/maintenance":
            data = [
                {"table": "sessions", "dead_tuples": 45000, "last_vacuum": "2026-05-20T03:00:00Z", "recommendation": "VACUUM ANALYZE sessions"},
                {"table": "orders", "dead_tuples": 1200, "last_vacuum": "2026-05-24T03:00:00Z", "recommendation": "OK — within threshold"},
            ]
        elif path == "/performance/index-usage":
            data = [
                {"index": "users_plan_idx", "table": "users", "scans": 12400, "size_mb": 0.8, "status": "active"},
                {"index": "orders_user_id_idx", "table": "orders", "scans": 89000, "size_mb": 3.2, "status": "active"},
                {"index": "orders_created_at_idx", "table": "orders", "scans": 0, "size_mb": 4.1, "status": "unused — consider dropping"},
            ]
        elif path == "/migrations":
            data = [
                {"id": 1, "name": "001_create_users", "applied_at": "2023-01-01T00:00:00Z", "duration_ms": 45},
                {"id": 2, "name": "002_create_orders", "applied_at": "2023-02-15T00:00:00Z", "duration_ms": 32},
                {"id": 3, "name": "003_add_sessions", "applied_at": "2023-06-01T00:00:00Z", "duration_ms": 28},
                {"id": 4, "name": "004_add_email_verified", "applied_at": "2026-05-01T00:00:00Z", "duration_ms": 15},
            ]
        else:
            data = {"path": path, "status": "ok"}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path

        if path == "/query":
            sql = body.get("sql", "").lower()
            if "count" in sql:
                data = {"columns": ["count"], "rows": [[48500]], "row_count": 1, "duration_ms": 3}
            elif "users" in sql:
                data = {"columns": ["id", "email", "plan"], "rows": [["u-001", "alice@acme.com", "enterprise"], ["u-003", "carol@bigcorp.com", "enterprise"]], "row_count": 2, "duration_ms": 12}
            else:
                data = {"columns": ["id"], "rows": [["1"]], "row_count": 1, "duration_ms": 5}
        elif path == "/query/explain":
            data = {
                "plan": [
                    "Seq Scan on users  (cost=0.00..1234.00 rows=8100 width=64)",
                    "  Filter: (plan = 'enterprise')",
                    "  Rows Removed by Filter: 40400",
                ],
                "estimated_cost": 1234.0,
                "estimated_rows": 8100,
                "recommendation": "Consider adding index on 'plan' column for better performance",
            }
        elif path == "/query/validate":
            sql = body.get("sql", "")
            valid = sql.strip().upper().startswith("SELECT") or sql.strip().upper().startswith("INSERT") or sql.strip().upper().startswith("UPDATE") or sql.strip().upper().startswith("ALTER") or sql.strip().upper().startswith("CREATE")
            data = {"valid": valid, "message": "SQL syntax is valid" if valid else "Invalid SQL syntax"}
        elif path == "/execute":
            data = {"affected_rows": 1, "duration_ms": 5, "message": "Statement executed successfully"}
        elif path == "/schema/indexes":
            cols = body.get("columns", ["col"])
            table = body.get("table", "table")
            name = f"{table}_{'_'.join(cols)}_idx"
            data = {"created": True, "index_name": name, "message": f"CREATE INDEX {name} ON {table} ({', '.join(cols)})"}
        elif path == "/migrations/run":
            data = {"applied": True, "name": body.get("name", "migration"), "duration_ms": 45, "message": f"Migration '{body.get('name')}' applied successfully"}
        elif "/filter" in path:
            table = path.split("/")[2]
            limit = body.get("limit", 50)
            data = {"rows": SAMPLE_USERS[:limit] if table == "users" else SAMPLE_ORDERS[:limit], "total": 48500 if table == "users" else 125000, "page": 1}
        elif path == "/utils/generate-schema":
            desc = body.get("description", "")
            data = {
                "sql": f"CREATE TABLE events (\n  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),\n  name VARCHAR(100) NOT NULL,\n  payload JSONB,\n  created_at TIMESTAMPTZ NOT NULL DEFAULT now()\n);",
                "description": desc,
            }
        else:
            data = {"ok": True, "path": path}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def log_message(self, format, *args):
        pass  # Suppress request logs


if __name__ == "__main__":
    port = 7799
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"🗄️  Database test backend running on http://localhost:{port}")
    print(f"   Connect mcp-database: DATABASE_API_URL=http://localhost:{port} mcp-database")
    print(f"   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
