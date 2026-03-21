from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from core.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class Settings:
    """
    Environment-driven settings.

    Do not place secrets in git; use .env for local development only.
    """

    app_env: str
    app_name: str
    log_level: str
    config_path: Path
    logs_dir: Path


DEFAULT_CONFIG_PATH = Path("config") / "model_router.json"
DEFAULT_LOGS_DIR = Path("logs")


def _as_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    return Path(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Load environment variables (and .env if present) and return Settings.

    Cached for process consistency.
    """
    # Safe if .env doesn't exist; load_dotenv() simply does nothing.
    load_dotenv()

    app_env = (os.getenv("APP_ENV", "development") or "development").strip()
    app_name = (os.getenv("APP_NAME", "AtlasKernel") or "AtlasKernel").strip()
    log_level = (os.getenv("LOG_LEVEL", "INFO") or "INFO").strip()

    config_path = _as_path(os.getenv("CONFIG_PATH"), DEFAULT_CONFIG_PATH)
    logs_dir = _as_path(os.getenv("LOGS_DIR"), DEFAULT_LOGS_DIR)

    return Settings(
        app_env=app_env,
        app_name=app_name,
        log_level=log_level,
        config_path=config_path,
        logs_dir=logs_dir,
    )


def load_json_config(path: Path | str | None = None) -> dict[str, Any]:
    """
    Load JSON config with safe fallbacks.

    Behavior:
    - missing file => {}
    - invalid JSON => {}
    - non-object root => {}
    """
    settings = get_settings()
    cfg_path = Path(path) if path is not None else settings.config_path

    try:
        if not cfg_path.exists():
            log.warning("config missing; using empty config", extra={"path": str(cfg_path)})
            return {}

        raw = cfg_path.read_text(encoding="utf-8")
        parsed = json.loads(raw)

        if not isinstance(parsed, dict):
            log.warning("config root is not an object; using empty config", extra={"path": str(cfg_path)})
            return {}

        return parsed
    except json.JSONDecodeError:
        log.exception("invalid json config; using empty config", extra={"path": str(cfg_path)})
        return {}
    except Exception:
        log.exception("failed to load config; using empty config", extra={"path": str(cfg_path)})
        return {}
