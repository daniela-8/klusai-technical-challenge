"""Application configuration loaded from environment variables."""

from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — every value can be overridden via .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    openai_model: str = "gpt-4o"
    openai_model_mini: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    database_url: str = "sqlite+aiosqlite:///./data/klusai.db"
    chroma_persist_dir: str = "./data/chromadb"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:3000"
    log_level: str = "INFO"
    max_concurrent_scrapes: int = 5
    scrape_timeout: int = 30
    scrape_user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
    use_mock_fallback: bool = True
    serper_api_key: str = ""
    gemini_api_key: str = ""

    @property
    def data_dir(self) -> Path:
        return Path("./data")

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key) and self.openai_api_key not in (
            "sk-your-key-here",
            "",
        )

    @property
    def has_serper_key(self) -> bool:
        return bool(self.serper_api_key) and self.serper_api_key not in (
            "",
            "your-key-here",
        )

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key) and self.gemini_api_key not in (
            "",
            "your-key-here",
        )


settings = Settings()
