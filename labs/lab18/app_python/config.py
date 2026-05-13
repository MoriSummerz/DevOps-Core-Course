from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env")

    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    visits_file: str = "/data/visits"


settings = Settings.model_validate({})
