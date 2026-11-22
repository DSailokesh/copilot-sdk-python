"""Settings from environment variables (App Service: Configuration > Application settings)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Local development: read .env into the environment (real env vars take precedence).
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # Model ID (Anthropic API) or deployment name (Foundry). Empty = the SDK's default.
    model: str | None = os.getenv("AGENT_MODEL") or None
    # Limits for one question.
    max_turns: int = int(os.getenv("AGENT_MAX_TURNS", "6"))
    max_web_searches: int = int(os.getenv("AGENT_MAX_WEB_SEARCHES", "3"))
    timeout_seconds: int = int(os.getenv("AGENT_TIMEOUT_SECONDS", "120"))
    max_concurrent: int = int(os.getenv("AGENT_MAX_CONCURRENT", "3"))
    # Time zone used to tell the agent what "today" means.
    time_zone: str = os.getenv("APP_TIME_ZONE", "Asia/Kolkata")
    # Writable folder for each run's empty working directory.
    work_root: str = os.getenv("AGENT_WORK_ROOT", "/tmp/agent-runs")


settings = Settings()
