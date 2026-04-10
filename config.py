"""
Saves and loads app settings (including API key) to a file in the user's
home directory: ~/.act_enrichment/config.json
"""

import json
from pathlib import Path

_CONFIG_DIR = Path.home() / ".act_enrichment"
_CONFIG_FILE = _CONFIG_DIR / "config.json"


def load() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            return {}
    return {}


def save(data: dict):
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(data, indent=2))


def get_api_key() -> str | None:
    return load().get("api_key")


def set_api_key(key: str):
    data = load()
    data["api_key"] = key
    save(data)
