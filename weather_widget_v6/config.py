from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "weather-widget"
SETTINGS_FILE = APP_DIR / "settings.json"
CACHE_FILE = APP_DIR / "cache.json"

DEFAULT_SETTINGS = {
    "manual_city": "",
    "favorites": ["Valencia", "Madrid", "Barcelona"],
    "theme": "Atmospheric",
    "units": "metric",
    "update_minutes": 15,
    "animations": True,
    "opacity": 0.84,
    "compact": False,
    "position": None,
}


def _ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    _ensure_dir()
    data = DEFAULT_SETTINGS.copy()
    try:
        if SETTINGS_FILE.exists():
            data.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError):
        pass
    return data


def save_settings(settings: dict) -> None:
    _ensure_dir()
    SETTINGS_FILE.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def load_cache() -> dict | None:
    _ensure_dir()
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        pass
    return None


def save_cache(payload: dict) -> None:
    _ensure_dir()
    CACHE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
