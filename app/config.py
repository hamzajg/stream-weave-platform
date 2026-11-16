from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "StreamWeave Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Database - SQLite for dev, PostgreSQL for prod
    database_url: str = "sqlite:///./streamweave.db"
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    access_token_expire_minutes: int = 30
    password_reset_expire_minutes: int = 30
    
    # CORS — comma-separated browser origins allowed to call the API.
    # Defaults to the Vite dev server; the bundled SPA is served same-origin
    # from `app/static` and needs no entry. Never use "*" here: it cannot be
    # combined with credentials (browsers reject the response), so wildcards
    # are dropped and logged at startup.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Static files
    static_dir: str = "static"
    
    # External Services (for future iterations)
    autogen_studio_url: str = "http://localhost:8080"
    ollama_url: str = "http://localhost:11434"

    # Agent runtime — OpenAI-compatible chat endpoint (Ollama exposes one
    # at {ollama_url}/v1; any compatible server works).
    agent_llm_base_url: str = ""  # empty → derived from ollama_url + "/v1"
    agent_llm_api_key: str = ""   # optional; Ollama needs none
    agent_llm_model: str = "llama3.1"
    agent_max_iterations: int = 6
    agent_max_history: int = 20
    
    @property
    def cors_origin_list(self) -> list:
        """Configured CORS origins, stripped of whitespace and empties."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    if not settings.agent_llm_base_url:
        settings.agent_llm_base_url = settings.ollama_url.rstrip("/") + "/v1"
    return settings
