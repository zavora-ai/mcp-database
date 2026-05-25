use crate::client::DbBackend;
use rmcp::{handler::server::wrapper::Parameters, schemars, tool, tool_router};
use serde_json::json;

#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct EmptyInput {}
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct NameInput { pub name: String }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct QueryInput { pub sql: String, pub params: Option<Vec<serde_json::Value>>, pub limit: Option<u32> }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct TableInput { pub table: String, pub schema: Option<String> }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct ExplainInput { pub sql: String }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct SampleInput { pub table: String, pub limit: Option<u32> }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct SearchInput { pub query: String }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct MigrationInput { pub name: String, pub sql_up: String, pub sql_down: Option<String> }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct IndexInput { pub table: String, pub columns: Vec<String>, pub unique: Option<bool> }
#[derive(Debug, serde::Deserialize, schemars::JsonSchema)]
pub struct FilterInput { pub table: String, pub filter: Option<serde_json::Value>, pub limit: Option<u32>, pub offset: Option<u32>, pub order_by: Option<String> }

#[derive(Clone)]
pub struct DbServer { pub backend: DbBackend }

fn r(result: Result<serde_json::Value, anyhow::Error>) -> String {
    match result { Ok(v) => serde_json::to_string_pretty(&v).unwrap(), Err(e) => format!("Error: {}", e) }
}

#[tool_router(server_handler)]
impl DbServer {
    // === Schema Inspection (6) ===

    #[tool(description = "List all tables/collections in the database")]
    async fn list_tables(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/schema/tables").await)
    }

    #[tool(description = "Get table schema: columns, types, constraints, indexes")]
    async fn describe_table(&self, Parameters(input): Parameters<TableInput>) -> String {
        let schema = input.schema.unwrap_or("public".into());
        r(self.backend.get(&format!("/schema/tables/{}?schema={}", input.table, schema)).await)
    }

    #[tool(description = "Get foreign key relationships for a table")]
    async fn get_relationships(&self, Parameters(input): Parameters<TableInput>) -> String {
        r(self.backend.get(&format!("/schema/tables/{}/relationships", input.table)).await)
    }

    #[tool(description = "List all indexes on a table")]
    async fn list_indexes(&self, Parameters(input): Parameters<TableInput>) -> String {
        r(self.backend.get(&format!("/schema/tables/{}/indexes", input.table)).await)
    }

    #[tool(description = "Get database size, table sizes, and row counts")]
    async fn get_database_stats(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/schema/stats").await)
    }

    #[tool(description = "Search for tables or columns by name")]
    async fn search_schema(&self, Parameters(input): Parameters<SearchInput>) -> String {
        r(self.backend.get(&format!("/schema/search?q={}", urlencoding::encode(&input.query))).await)
    }

    // === Querying (5) ===

    #[tool(description = "Execute a read-only SQL query (SELECT only)")]
    async fn query(&self, Parameters(input): Parameters<QueryInput>) -> String {
        let limit = input.limit.unwrap_or(100);
        r(self.backend.post("/query", &json!({
            "sql": input.sql, "params": input.params, "limit": limit, "read_only": true
        })).await)
    }

    #[tool(description = "Get sample rows from a table")]
    async fn sample_data(&self, Parameters(input): Parameters<SampleInput>) -> String {
        let limit = input.limit.unwrap_or(10);
        r(self.backend.get(&format!("/tables/{}/sample?limit={}", input.table, limit)).await)
    }

    #[tool(description = "Query a table with filters, ordering, and pagination")]
    async fn filter_table(&self, Parameters(input): Parameters<FilterInput>) -> String {
        r(self.backend.post(&format!("/tables/{}/filter", input.table), &json!({
            "filter": input.filter, "limit": input.limit.unwrap_or(50),
            "offset": input.offset.unwrap_or(0), "order_by": input.order_by
        })).await)
    }

    #[tool(description = "Get EXPLAIN/query plan for a SQL statement")]
    async fn explain_query(&self, Parameters(input): Parameters<ExplainInput>) -> String {
        r(self.backend.post("/query/explain", &json!({"sql": input.sql})).await)
    }

    #[tool(description = "Get distinct values and counts for a column (useful for exploration)")]
    async fn get_column_stats(&self, Parameters(input): Parameters<TableInput>) -> String {
        let col = input.schema.unwrap_or("*".into());
        r(self.backend.get(&format!("/tables/{}/columns/{}/stats", input.table, col)).await)
    }

    // === Write Operations (4) ===

    #[tool(description = "Execute a write SQL statement (INSERT, UPDATE, DELETE) — requires confirmation")]
    async fn execute(&self, Parameters(input): Parameters<QueryInput>) -> String {
        r(self.backend.post("/execute", &json!({
            "sql": input.sql, "params": input.params
        })).await)
    }

    #[tool(description = "Create an index on a table")]
    async fn create_index(&self, Parameters(input): Parameters<IndexInput>) -> String {
        r(self.backend.post("/schema/indexes", &json!({
            "table": input.table, "columns": input.columns, "unique": input.unique.unwrap_or(false)
        })).await)
    }

    #[tool(description = "Run a migration (create/alter tables)")]
    async fn run_migration(&self, Parameters(input): Parameters<MigrationInput>) -> String {
        r(self.backend.post("/migrations/run", &json!({
            "name": input.name, "sql_up": input.sql_up, "sql_down": input.sql_down
        })).await)
    }

    #[tool(description = "List migration history (applied migrations)")]
    async fn list_migrations(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/migrations").await)
    }

    // === Performance (4) ===

    #[tool(description = "Get slow queries (queries exceeding duration threshold)")]
    async fn get_slow_queries(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/performance/slow-queries").await)
    }

    #[tool(description = "Get active connections and running queries")]
    async fn get_connections(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/performance/connections").await)
    }

    #[tool(description = "Get table bloat and vacuum recommendations")]
    async fn get_maintenance_status(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/performance/maintenance").await)
    }

    #[tool(description = "Get index usage stats — find unused or missing indexes")]
    async fn get_index_usage(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/performance/index-usage").await)
    }

    // === Utilities (3) ===

    #[tool(description = "Generate CREATE TABLE SQL from a description")]
    async fn generate_schema(&self, Parameters(input): Parameters<SearchInput>) -> String {
        r(self.backend.post("/utils/generate-schema", &json!({"description": input.query})).await)
    }

    #[tool(description = "Get ER diagram data (tables + relationships)")]
    async fn get_er_diagram(&self, Parameters(_): Parameters<EmptyInput>) -> String {
        r(self.backend.get("/schema/er-diagram").await)
    }

    #[tool(description = "Validate SQL syntax without executing")]
    async fn validate_sql(&self, Parameters(input): Parameters<ExplainInput>) -> String {
        r(self.backend.post("/query/validate", &json!({"sql": input.sql})).await)
    }
}
