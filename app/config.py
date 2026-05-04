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
    
    # Static files
    static_dir: str = "static"
    
    # External Services (for future iterations)
    autogen_studio_url: str = "http://localhost:8080"
    ollama_url: str = "http://localhost:11434"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
