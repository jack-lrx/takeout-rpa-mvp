from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = Field(default="Takeout RPA MVP")
    app_version: str = Field(default="0.1.0")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8000)
    database_path: Path = Field(default=BASE_DIR / "data" / "app.db")
    erp_mock_base_url: str = Field(default="http://127.0.0.1:8000")
    browser_user_data_dir: Path = Field(default=BASE_DIR / "data" / "browser")
    merchant_backend_url: str = Field(default="https://example.com/merchant")
    request_timeout_seconds: float = Field(default=10.0)
    network_log_truncate: int = Field(default=800)
    retry_batch_size: int = Field(default=100)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
