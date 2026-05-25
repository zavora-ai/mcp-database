# Testing mcp-database

## Quick Start

```bash
# From the mcp-database directory:
chmod +x test/run_tests.sh
./test/run_tests.sh
```

This will:
1. Build the binary (if needed)
2. Start the test backend on port 7799
3. Run all 22 tools via MCP protocol
4. Report pass/fail for each tool
5. Stop the test backend

## Manual Testing

### Step 1: Start the test backend

```bash
python3 test/test_server.py
```

Output:
```
🗄️  Database test backend running on http://localhost:7799
   Connect mcp-database: DATABASE_API_URL=http://localhost:7799 mcp-database
```

### Step 2: Run mcp-database

In another terminal:

```bash
DATABASE_API_URL="http://localhost:7799" ./target/debug/mcp-database
```

### Step 3: Send MCP requests

Pipe JSON-RPC messages to stdin:

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_tables","arguments":{}}}' | DATABASE_API_URL="http://localhost:7799" ./target/debug/mcp-database
```

## Test Backend API

The test server (`test_server.py`) implements all endpoints from the Custom API spec with realistic PostgreSQL-like data:

### Sample Data

- **4 tables**: users (48.5K rows), orders (125K), products (3.2K), sessions (890K)
- **5 sample users**: Alice (enterprise), Bob (pro), Carol (enterprise), Dan (free), Eve (pro)
- **3 sample orders**: with amounts, statuses, timestamps
- **4 migrations**: applied over time
- **3 slow queries**: with timing and call counts
- **Index usage**: active and unused indexes

### Endpoints Implemented

| Endpoint | Response |
|----------|----------|
| `GET /schema/tables` | 4 tables with row counts and sizes |
| `GET /schema/tables/:name` | Full schema with columns, types, constraints |
| `GET /schema/tables/:name/relationships` | Foreign key relationships |
| `GET /schema/tables/:name/indexes` | Index definitions |
| `GET /schema/stats` | Database-level statistics |
| `GET /schema/search?q=` | Search columns by name |
| `GET /schema/er-diagram` | ER diagram data |
| `POST /query` | Query results with columns and rows |
| `POST /query/explain` | Query plan with cost estimates |
| `POST /query/validate` | SQL syntax validation |
| `GET /tables/:name/sample` | Sample rows |
| `POST /tables/:name/filter` | Filtered query results |
| `GET /tables/:name/columns/:col/stats` | Column value distribution |
| `POST /execute` | Write result (affected rows) |
| `POST /schema/indexes` | Index creation confirmation |
| `POST /migrations/run` | Migration applied |
| `GET /migrations` | Migration history |
| `GET /performance/slow-queries` | Slow query list |
| `GET /performance/connections` | Connection pool status |
| `GET /performance/maintenance` | Vacuum recommendations |
| `GET /performance/index-usage` | Index scan statistics |
| `POST /utils/generate-schema` | Generated CREATE TABLE SQL |

## Using with a Real Database

To test against a real Supabase/Neon/PlanetScale instance:

```bash
# Supabase
SUPABASE_URL="https://xxx.supabase.co" SUPABASE_SERVICE_KEY="your-key" ./target/debug/mcp-database

# Neon
NEON_API_URL="https://console.neon.tech/api/v2" NEON_API_KEY="your-key" ./target/debug/mcp-database
```

## Expected Output

```
Results: 22/22 passed, 0 failed

  ✅ list_tables
  ✅ describe_table
  ✅ get_relationships
  ✅ list_indexes
  ✅ get_database_stats
  ✅ search_schema
  ✅ query
  ✅ sample_data
  ✅ filter_table
  ✅ explain_query
  ✅ get_column_stats
  ✅ execute
  ✅ create_index
  ✅ run_migration
  ✅ list_migrations
  ✅ get_slow_queries
  ✅ get_connections
  ✅ get_maintenance_status
  ✅ get_index_usage
  ✅ generate_schema
  ✅ get_er_diagram
  ✅ validate_sql

🎉 All tests passed!
```
