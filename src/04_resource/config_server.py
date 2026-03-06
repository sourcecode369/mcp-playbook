from fastmcp import FastMCP
import json, os
from dotenv import load_dotenv

load_dotenv()
mcp = FastMCP("config")

# Application config exposed as a resource
APP_CONFIG = {
    "app_name": "MyApp",
    "version": "2.1.0",
    "max_connections": 100,
    "features": {"dark_mode": True, "beta_features": False},
    "supported_languages": ["en", "es", "fr", "de", "ja"],
}

# Database schema exposed as a resource
DB_SCHEMA = {
    "users": {
        "columns": ["id", "email", "name", "created_at", "role"],
        "primary_key": "id",
        "indexes": ["email", "role"]
    },
    "orders": {
        "columns": ["id", "user_id", "total", "status", "created_at"],
        "primary_key": "id",
        "foreign_keys": {"user_id": "users.id"}
    }
}

@mcp.resource("config://app")
def get_app_config() -> str:
    """Current application configuration settings."""
    return json.dumps(APP_CONFIG, indent=2)

@mcp.resource("config://env/{key}")
def get_env_var(key: str) -> str:
    """
    Read a non-sensitive environment variable.
    Sensitive keys (containing TOKEN, SECRET, KEY, PASSWORD) are blocked.
    """
    blocked = ("TOKEN", "SECRET", "KEY", "PASSWORD", "CREDENTIAL")
    if any(b in key.upper() for b in blocked):
        return f"Access denied: '{key}' appears to be a sensitive variable."
    value = os.environ.get(key)
    if value is None:
        return f"Environment variable '{key}' is not set."
    return value

@mcp.resource("db://schema")
def get_db_schema() -> str:
    """Full database schema with table structures, columns, and relationships."""
    return json.dumps(DB_SCHEMA, indent=2)

@mcp.resource("db://schema/{table}")
def get_table_schema(table: str) -> str:
    """Schema for a specific database table."""
    if table not in DB_SCHEMA:
        return f"Table '{table}' not found. Available: {list(DB_SCHEMA.keys())}"
    return json.dumps({table: DB_SCHEMA[table]}, indent=2)

if __name__ == "__main__":
    mcp.run()