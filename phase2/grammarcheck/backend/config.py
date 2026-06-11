from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ollama_url: str = "http://localhost:11434/api/generate"
    ollama_model: str = "gemma4"
    database_url: str = "sqlite:///./grammarcheck.db"
    redis_url: str | None = None
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 256
    rate_limit_per_minute: int = 20
    api_key: str | None = None
    enable_api_key: bool = False
    log_level: str = "INFO"
    log_file: str | None = None
    max_input_length: int = 5000
    max_output_length: int = 10000
    enable_metrics: bool = True
    enable_eval: bool = True

    model_config = {"env_prefix": "GRAMMARCHECK_", "env_file": ".env"}


settings = Settings()
