use anyhow::{Result, bail};
use reqwest::Client;
use serde_json::Value;

#[derive(Clone)]
pub struct DbBackend {
    pub http: Client,
    pub base_url: String,
    pub auth_header: String,
    pub provider: String,
}

impl DbBackend {
    pub fn from_env() -> Result<Self> {
        // Supabase (PostgreSQL as a service)
        if let (Ok(url), Ok(key)) = (std::env::var("SUPABASE_URL"), std::env::var("SUPABASE_SERVICE_KEY")) {
            tracing::info!("Database backend: Supabase");
            return Ok(Self { http: Client::new(), base_url: format!("{}/rest/v1", url.trim_end_matches('/')), auth_header: format!("Bearer {}", key), provider: "supabase".into() });
        }
        // PlanetScale (MySQL)
        if let (Ok(url), Ok(token)) = (std::env::var("PLANETSCALE_URL"), std::env::var("PLANETSCALE_TOKEN")) {
            tracing::info!("Database backend: PlanetScale");
            return Ok(Self { http: Client::new(), base_url: url.trim_end_matches('/').to_string(), auth_header: format!("Bearer {}", token), provider: "planetscale".into() });
        }
        // Neon (PostgreSQL serverless)
        if let (Ok(url), Ok(token)) = (std::env::var("NEON_API_URL"), std::env::var("NEON_API_KEY")) {
            tracing::info!("Database backend: Neon");
            return Ok(Self { http: Client::new(), base_url: url.trim_end_matches('/').to_string(), auth_header: format!("Bearer {}", token), provider: "neon".into() });
        }
        // Custom API (wraps any database)
        if let Ok(url) = std::env::var("DATABASE_API_URL") {
            let key = std::env::var("DATABASE_API_KEY").unwrap_or_default();
            tracing::info!("Database backend: Custom API");
            return Ok(Self { http: Client::new(), base_url: url.trim_end_matches('/').to_string(), auth_header: format!("Bearer {}", key), provider: "custom".into() });
        }
        bail!("No database backend. Set SUPABASE_URL+SUPABASE_SERVICE_KEY, PLANETSCALE_URL+PLANETSCALE_TOKEN, NEON_API_URL+NEON_API_KEY, or DATABASE_API_URL")
    }

    pub async fn get(&self, path: &str) -> Result<Value> {
        let resp = self.http.get(format!("{}{}", self.base_url, path))
            .header("Authorization", &self.auth_header)
            .header("apikey", self.auth_header.trim_start_matches("Bearer "))
            .send().await?;
        if !resp.status().is_success() { bail!("DB API {}: {}", resp.status(), resp.text().await?); }
        Ok(resp.json().await?)
    }

    pub async fn post(&self, path: &str, body: &Value) -> Result<Value> {
        let resp = self.http.post(format!("{}{}", self.base_url, path))
            .header("Authorization", &self.auth_header)
            .header("apikey", self.auth_header.trim_start_matches("Bearer "))
            .json(body).send().await?;
        if !resp.status().is_success() { bail!("DB API {}: {}", resp.status(), resp.text().await?); }
        Ok(resp.json().await?)
    }
}
