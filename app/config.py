from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    database_url: str
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    ai_provider: str = "openai"
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    default_language: str = "en"
    batch_size: int = 30
    under_rated_threshold: int = 10

    # polling — локально; webhook — Railway / production
    bot_mode: str = "polling"
    webhook_url: str = ""
    webhook_path: str = "/webhook"
    webhook_secret: str = ""
    railway_public_domain: str = ""
    port: int = Field(default=8080, validation_alias="PORT")

    def resolved_webhook_url(self) -> str:
        if self.webhook_url:
            return self.webhook_url.rstrip("/")
        if self.railway_public_domain:
            domain = self.railway_public_domain.removeprefix("https://").removeprefix("http://")
            return f"https://{domain.rstrip('/')}{self.webhook_path}"
        return ""

    @property
    def is_webhook(self) -> bool:
        return self.bot_mode.lower() == "webhook"


settings = Settings()
