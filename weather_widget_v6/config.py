from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path.home() / ".config" / "weather-widget"
SETTINGS_FILE = APP_DIR / "settings.json"
CACHE_FILE = APP_DIR / "cache.json"
CONFIG_VERSION = 2

DEFAULT_SETTINGS = {
    "config_version": CONFIG_VERSION,
    "manual_city": "",
    "favorites": ["Valencia", "Madrid", "Barcelona"],
    "theme": "Atmospheric",
    "units": "metric",
    "update_minutes": 15,
    "animations": True,
    "opacity": 0.55,
    "compact": False,
    "position": None,
}


def _ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    _ensure_dir()
    data = DEFAULT_SETTINGS.copy()
    loaded = {}
    try:
        if SETTINGS_FILE.exists():
            loaded = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                data.update(loaded)
    except (OSError, ValueError, TypeError):
        loaded = {}

    # V1 stored an almost opaque 0.92 value. Migrate existing installs once
    # so V6 actually looks like a glass/translucent desktop widget.
    version = int(loaded.get("config_version", 1)) if isinstance(loaded, dict) else 1
    if version < CONFIG_VERSION:
        data["opacity"] = 0.55
        data["config_version"] = CONFIG_VERSION
        try:
            save_settings(data)
        except OSError:
            pass

    try:
        data["opacity"] = min(0.90, max(0.25, float(data.get("opacity", 0.55))))
    except (TypeError, ValueError):
        data["opacity"] = 0.55
    return data


def save_settings(settings: dict) -> None:
    _ensure_dir()
    settings["config_version"] = CONFIG_VERSION
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
