# Database MCP Server

[![Crates.io](https://img.shields.io/crates/v/mcp-database.svg)](https://crates.io/crates/mcp-database)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![ADK-Rust Enterprise](https://img.shields.io/badge/ADK--Rust-Enterprise-purple.svg)](https://enterprise.adk-rust.com)
[![Registry Ready](https://img.shields.io/badge/ADK_Registry-Ready-green.svg)](https://www.zavora.ai)

Database operations for AI agents — query, schema inspection, migrations, explain plans, performance analysis, and data exploration. 22 tools with read-only defaults and governed writes.

## Architecture

<p align="center">
  <img src="https://raw.githubusercontent.com/zavora-ai/mcp-database/main/docs/assets/architecture.svg" alt="MCP Database Architecture" width="850"/>
</p>

## Tools (22)

### Schema Inspection (6)

| Tool | Purpose |
|------|---------|
| `list_tables` | All tables/collections in the database |
| `describe_table` | Columns, types, constraints, indexes |
| `get_relationships` | Foreign keys and references |
| `list_indexes` | All indexes on a table |
| `get_database_stats` | DB size, table sizes, row counts |
| `search_schema` | Find tables/columns by name |

### Querying (5)

| Tool | Purpose | Risk |
|------|---------|------|
| `query` | Execute read-only SQL (SELECT only) | read_only |
| `sample_data` | Get sample rows from a table | read_only |
| `filter_table` | Query with filters, ordering, pagination | read_only |
| `explain_query` | Get EXPLAIN/query plan | read_only |
| `get_column_stats` | Distinct values and distributions | read_only |

### Write Operations (4)

| Tool | Purpose | Risk |
|------|---------|------|
| `execute` | Run INSERT/UPDATE/DELETE | **gated_write** |
| `create_index` | Create an index | internal_write |
| `run_migration` | Apply a schema migration | **gated_write** |
| `list_migrations` | View migration history | read_only |

### Performance (4)

| Tool | Purpose |
|------|---------|
| `get_slow_queries` | Queries exceeding duration threshold |
| `get_connections` | Active connections and running queries |
| `get_maintenance_status` | Table bloat, vacuum recommendations |
| `get_index_usage` | Unused or missing indexes |

### Utilities (3)

| Tool | Purpose |
|------|---------|
| `generate_schema` | Generate CREATE TABLE from description |
| `get_er_diagram` | ER diagram data (tables + relationships) |
| `validate_sql` | Check SQL syntax without executing |

## Installation

```bash
cargo install mcp-database
```

## Configuration

| Backend | Env Vars | Database |
|---------|----------|----------|
| **Supabase** | `SUPABASE_URL` + `SUPABASE_SERVICE_KEY` | PostgreSQL |
| **PlanetScale** | `PLANETSCALE_URL` + `PLANETSCALE_TOKEN` | MySQL |
| **Neon** | `NEON_API_URL` + `NEON_API_KEY` | PostgreSQL (serverless) |
| **Custom API** | `DATABASE_API_URL` + `DATABASE_API_KEY` | Any (Postgres, MySQL, Mongo, SQLite) |

## Client Configuration

```json
{
  "mcpServers": {
    "database": {
      "command": "mcp-database",
      "args": [],
      "env": {
        "SUPABASE_URL": "https://xxx.supabase.co",
        "SUPABASE_SERVICE_KEY": "your-service-key"
      }
    }
  }
}
```

## Usage Examples

### Explore a database
```
"What tables are in this database?"
→ list_tables()
→ describe_table(table="users")
→ get_relationships(table="orders")
→ sample_data(table="users", limit=5)
```

### Debug a slow query
```
"Why is this query slow?"
→ explain_query(sql="SELECT * FROM orders JOIN users ON ...")
→ get_index_usage() — find missing indexes
→ create_index(table="orders", columns=["user_id"])
```

### Data exploration
```
"How many users signed up this month?"
→ query(sql="SELECT COUNT(*) FROM users WHERE created_at >= '2026-05-01'")
→ get_column_stats(table="users", schema="plan") — distribution by plan
```

### Run a migration
```
"Add an email_verified column to users"
→ run_migration(name="add_email_verified", sql_up="ALTER TABLE users ADD COLUMN email_verified BOOLEAN DEFAULT false")
```

## Governance

- **Read-only by default** — `query` tool only allows SELECT statements
- **Writes are gated** — `execute` and `run_migration` are classified as gated writes
- **No data stored** — MCP is a pure API passthrough
- **Parameterized queries** — prevents SQL injection via params array

## Custom API Spec

Build your own backend implementing these endpoints:

```
GET    /schema/tables
GET    /schema/tables/:name
GET    /schema/tables/:name/relationships
GET    /schema/tables/:name/indexes
GET    /schema/stats
GET    /schema/search?q=
GET    /schema/er-diagram
POST   /query                    {sql, params, limit, read_only}
POST   /query/explain            {sql}
POST   /query/validate           {sql}
GET    /tables/:name/sample?limit=
POST   /tables/:name/filter      {filter, limit, offset, order_by}
GET    /tables/:name/columns/:col/stats
POST   /execute                  {sql, params}
POST   /schema/indexes           {table, columns, unique}
POST   /migrations/run           {name, sql_up, sql_down}
GET    /migrations
GET    /performance/slow-queries
GET    /performance/connections
GET    /performance/maintenance
GET    /performance/index-usage
POST   /utils/generate-schema    {description}
```

## License

Apache-2.0

---

Part of the [ADK-Rust Enterprise](https://enterprise.adk-rust.com) MCP server ecosystem.

Built with ❤️ by [Zavora AI](https://zavora.ai)
