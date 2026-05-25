mod client;
mod server;

use client::DbBackend;
use rmcp::{ServiceExt, transport::stdio};
use server::DbServer;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().with_env_filter(tracing_subscriber::EnvFilter::from_default_env()).init();
    let backend = DbBackend::from_env()?;
    let service = DbServer { backend }.serve(stdio()).await?;
    service.waiting().await?;
    Ok(())
}
