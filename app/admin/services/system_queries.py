import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import asyncpg

from app.config import settings
from app.utils.scoring import SCORING_CALIBRATION_VERSION


@dataclass(frozen=True)
class EnvFlag:
    name: str
    value: str
    is_secret: bool


@dataclass(frozen=True)
class SystemInfo:
    git_commit: str | None
    calibration_version: int
    bot_mode: str
    is_webhook: bool
    admin_enabled: bool
    env_flags: list[EnvFlag]
    event_log_count: int
    action_log_count: int
    migration_count: int


class SystemQueries:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def fetch_info(self) -> SystemInfo:
        event_log_count = await self._pool.fetchval(
            "select count(*)::int from admin_event_log"
        )
        action_log_count = await self._pool.fetchval(
            "select count(*)::int from admin_action_log"
        )
        migration_count = await self._pool.fetchval(
            "select count(*)::int from schema_migrations"
        )
        return SystemInfo(
            git_commit=_git_commit(),
            calibration_version=SCORING_CALIBRATION_VERSION,
            bot_mode=settings.bot_mode,
            is_webhook=settings.is_webhook,
            admin_enabled=bool(settings.admin_password),
            env_flags=_env_flags(),
            event_log_count=event_log_count or 0,
            action_log_count=action_log_count or 0,
            migration_count=migration_count or 0,
        )


def _git_commit() -> str | None:
    env_commit = os.environ.get("RAILWAY_GIT_COMMIT_SHA") or os.environ.get("GIT_COMMIT")
    if env_commit:
        return env_commit[:12]
    root = Path(__file__).resolve().parents[3]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _env_flags() -> list[EnvFlag]:
    def flag(name: str, value: str, *, secret: bool = False) -> EnvFlag:
        if secret:
            display = "set" if value else "missing"
        else:
            display = value or "(empty)"
        return EnvFlag(name=name, value=display, is_secret=secret)

    return [
        flag("BOT_MODE", settings.bot_mode),
        flag("AI_PROVIDER", settings.ai_provider),
        flag("DEFAULT_LANGUAGE", settings.default_language),
        flag("BATCH_SIZE", str(settings.batch_size)),
        flag("TELEGRAM_BOT_TOKEN", settings.telegram_bot_token, secret=True),
        flag("DATABASE_URL", settings.database_url, secret=True),
        flag("OPENAI_API_KEY", settings.openai_api_key, secret=True),
        flag("ADMIN_PASSWORD", settings.admin_password, secret=True),
        flag("WEBHOOK_URL", settings.resolved_webhook_url() or settings.webhook_url),
    ]
