"""
Real SQLite backend for mcp-database.
Creates an actual database, runs real SQL, and cleans up.

Usage:
    python3 test_sqlite_backend.py
    # Runs on http://localhost:7799
    # Creates test.db in current directory
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json, sqlite3, os, time

DB_PATH = "test.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        params = {}
        if "?" in self.path:
            for p in self.path.split("?")[1].split("&"):
                if "=" in p:
                    k, v = p.split("=", 1)
                    params[k] = v

        conn = get_conn()
        conn.row_factory = dict_factory

        try:
            if path == "/schema/tables":
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = []
                for row in cur.fetchall():
                    name = row["name"]
                    count = conn.execute(f"SELECT COUNT(*) as c FROM [{name}]").fetchone()["c"]
                    tables.append({"name": name, "row_count": count})
                data = tables

            elif path.startswith("/schema/tables/") and not path.endswith("/relationships") and not path.endswith("/indexes"):
                table = path.split("/")[3]
                cur = conn.execute(f"PRAGMA table_info([{table}])")
                columns = [{"name": r["name"], "type": r["type"], "nullable": r["notnull"] == 0, "primary_key": r["pk"] == 1, "default": r["dflt_value"]} for r in cur.fetchall()]
                count = conn.execute(f"SELECT COUNT(*) as c FROM [{table}]").fetchone()["c"]
                data = {"table": table, "columns": columns, "row_count": count}

            elif path.endswith("/relationships"):
                table = path.split("/")[3]
                cur = conn.execute(f"PRAGMA foreign_key_list([{table}])")
                rels = [{"from_table": table, "from_column": r["from"], "to_table": r["table"], "to_column": r["to"]} for r in cur.fetchall()]
                data = rels

            elif path.endswith("/indexes"):
                table = path.split("/")[3]
                cur = conn.execute(f"PRAGMA index_list([{table}])")
                indexes = []
                for idx in cur.fetchall():
                    cols_cur = conn.execute(f"PRAGMA index_info([{idx['name']}])")
                    cols = [c["name"] for c in cols_cur.fetchall()]
                    indexes.append({"name": idx["name"], "columns": cols, "unique": idx["unique"] == 1})
                data = indexes

            elif path == "/schema/stats":
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = []
                total = 0
                for row in cur.fetchall():
                    count = conn.execute(f"SELECT COUNT(*) as c FROM [{row['name']}]").fetchone()["c"]
                    tables.append({"name": row["name"], "row_count": count})
                    total += count
                size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
                data = {"database_size_bytes": size, "tables": tables, "total_rows": total}

            elif path.startswith("/schema/search"):
                q = params.get("q", "").lower()
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                results = []
                for row in cur.fetchall():
                    cols = conn.execute(f"PRAGMA table_info([{row['name']}])").fetchall()
                    for col in cols:
                        if q in col["name"].lower() or q in row["name"].lower():
                            results.append({"table": row["name"], "column": col["name"], "type": col["type"]})
                data = results

            elif path == "/schema/er-diagram":
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                tables = [r["name"] for r in cur.fetchall()]
                rels = []
                for t in tables:
                    fks = conn.execute(f"PRAGMA foreign_key_list([{t}])").fetchall()
                    for fk in fks:
                        rels.append({"from": f"{t}.{fk['from']}", "to": f"{fk['table']}.{fk['to']}"})
                data = {"tables": tables, "relationships": rels}

            elif "/sample" in path:
                table = path.split("/")[2]
                limit = int(params.get("limit", "10"))
                cur = conn.execute(f"SELECT * FROM [{table}] LIMIT ?", (limit,))
                data = cur.fetchall()

            elif "/columns/" in path and "/stats" in path:
                parts = path.split("/")
                table = parts[2]
                col = parts[4]
                cur = conn.execute(f"SELECT [{col}], COUNT(*) as count FROM [{table}] GROUP BY [{col}] ORDER BY count DESC LIMIT 20")
                values = [{"value": r[col], "count": r["count"]} for r in cur.fetchall()]
                total = conn.execute(f"SELECT COUNT(DISTINCT [{col}]) as c FROM [{table}]").fetchone()["c"]
                data = {"column": col, "distinct_count": total, "values": values}

            elif path == "/performance/slow-queries":
                data = [{"message": "SQLite does not track slow queries. Use EXPLAIN QUERY PLAN for optimization."}]

            elif path == "/performance/connections":
                data = {"active": 1, "max": 1, "note": "SQLite is single-connection"}

            elif path == "/performance/maintenance":
                size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
                data = [{"database_size_bytes": size, "recommendation": "Run VACUUM to reclaim space" if size > 1000000 else "Database is small, no maintenance needed"}]

            elif path == "/performance/index-usage":
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
                data = [{"index": r["name"], "note": "SQLite does not expose index usage stats"} for r in cur.fetchall()]

            elif path == "/migrations":
                try:
                    cur = conn.execute("SELECT * FROM _migrations ORDER BY id")
                    data = cur.fetchall()
                except:
                    data = []

            else:
                data = {"path": path, "status": "not_found"}

        except Exception as e:
            data = {"error": str(e)}

        conn.close()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        path = self.path
        conn = get_conn()
        conn.row_factory = dict_factory

        try:
            if path == "/query":
                sql = body.get("sql", "")
                params = body.get("params") or []
                if not isinstance(params, list):
                    params = []
                limit = body.get("limit", 100)
                # Enforce read-only
                if body.get("read_only", True):
                    if not sql.strip().upper().startswith("SELECT"):
                        data = {"error": "Only SELECT queries allowed in read-only mode"}
                        self._respond(data); conn.close(); return
                start = time.time()
                cur = conn.execute(sql + f" LIMIT {limit}" if "LIMIT" not in sql.upper() else sql, params)
                rows = cur.fetchall()
                columns = [desc[0] for desc in cur.description] if cur.description else []
                duration = round((time.time() - start) * 1000, 2)
                data = {"columns": columns, "rows": rows, "row_count": len(rows), "duration_ms": duration}

            elif path == "/query/explain":
                sql = body.get("sql", "")
                cur = conn.execute(f"EXPLAIN QUERY PLAN {sql}")
                plan = [f"{r['detail']}" for r in cur.fetchall()]
                data = {"plan": plan}

            elif path == "/query/validate":
                sql = body.get("sql", "")
                try:
                    conn.execute(f"EXPLAIN {sql}")
                    data = {"valid": True, "message": "SQL syntax is valid"}
                except Exception as e:
                    data = {"valid": False, "message": str(e)}

            elif path == "/execute":
                sql = body.get("sql", "")
                params = body.get("params") or []
                if params and not isinstance(params, list):
                    params = []
                start = time.time()
                cur = conn.execute(sql, params)
                conn.commit()
                duration = round((time.time() - start) * 1000, 2)
                data = {"affected_rows": cur.rowcount, "duration_ms": duration}

            elif path == "/schema/indexes":
                table = body.get("table", "")
                columns = body.get("columns", [])
                unique = body.get("unique", False)
                name = f"idx_{table}_{'_'.join(columns)}"
                unique_str = "UNIQUE " if unique else ""
                sql = f"CREATE {unique_str}INDEX [{name}] ON [{table}] ({', '.join(f'[{c}]' for c in columns)})"
                conn.execute(sql)
                conn.commit()
                data = {"created": True, "index_name": name, "sql": sql}

            elif path == "/migrations/run":
                name = body.get("name", "unnamed")
                sql_up = body.get("sql_up", "")
                # Create migrations table if needed
                conn.execute("CREATE TABLE IF NOT EXISTS _migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, sql_up TEXT, applied_at TEXT)")
                start = time.time()
                conn.execute(sql_up)
                conn.execute("INSERT INTO _migrations (name, sql_up, applied_at) VALUES (?, ?, datetime('now'))", (name, sql_up))
                conn.commit()
                duration = round((time.time() - start) * 1000, 2)
                data = {"applied": True, "name": name, "duration_ms": duration}

            elif "/filter" in path:
                table = path.split("/")[2]
                limit = body.get("limit", 50)
                offset = body.get("offset", 0)
                order_by = body.get("order_by", "rowid")
                cur = conn.execute(f"SELECT * FROM [{table}] ORDER BY [{order_by}] LIMIT ? OFFSET ?", (limit, offset))
                rows = cur.fetchall()
                total = conn.execute(f"SELECT COUNT(*) as c FROM [{table}]").fetchone()["c"]
                data = {"rows": rows, "total": total, "limit": limit, "offset": offset}

            elif path == "/utils/generate-schema":
                desc = body.get("description", "")
                # Simple heuristic
                data = {"sql": f"-- Generated from: {desc}\nCREATE TABLE new_table (\n  id INTEGER PRIMARY KEY AUTOINCREMENT,\n  created_at TEXT DEFAULT (datetime('now'))\n);", "note": "Customize this template based on your needs"}

            else:
                data = {"ok": True, "path": path}

        except Exception as e:
            data = {"error": str(e)}

        conn.close()
        self._respond(data)

    def _respond(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def log_message(self, *args): pass


if __name__ == "__main__":
    # Clean start
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    port = 7799
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"🗄️  SQLite backend running on http://localhost:{port}")
    print(f"   Database: {os.path.abspath(DB_PATH)}")
    print(f"   Connect: DATABASE_API_URL=http://localhost:{port} mcp-database")
    print(f"   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
            print(f"Cleaned up {DB_PATH}")
