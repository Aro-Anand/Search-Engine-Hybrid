"""
Configuration Management Module

Centralized configuration using Pydantic Settings for environment variables.

Author: Development Team
Version: 1.0.0
"""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Settings can be overridden by creating a .env file in the project root.
    
    Example .env file:
        ENVIRONMENT=production
        API_HOST=0.0.0.0
        API_PORT=9999
        MODEL_NAME=all-MiniLM-L6-v2
    """
    
    # Environment
    environment: str = Field(default="development", description="Environment: development, staging, production")
    
    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host address")
    api_port: int = Field(default=9999, description="API port")
    api_workers: int = Field(default=2, description="Number of worker processes")
    
    # Model Settings
    model_name: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model name")
    embedding_cache_size: int = Field(default=1000, description="Embedding cache size")
    
    # Search Settings
    max_query_length: int = Field(default=200, description="Maximum query length in characters")
    default_top_k: int = Field(default=10, description="Default number of results to return")
    max_top_k: int = Field(default=100, description="Maximum number of results allowed")
    
    # Scoring Weights
    keyword_weight: float = Field(default=0.4, description="Weight for keyword scoring")
    semantic_weight: float = Field(default=0.6, description="Weight for semantic scoring")
    
    # CORS Settings
    allowed_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins (comma-separated in .env)"
    )
    
    # Logging
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")
    log_file: str = Field(default="/var/log/semantic-search/app.log", description="Log file path")
    
    # Data
    data_path: str = Field(default="data/listings.json", description="Path to listings data file")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=100, description="Max requests per minute per IP")
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()