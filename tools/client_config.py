"""Чтение и проверка персональной конфигурации клиента."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CLIENT_CONFIG = ROOT / "client.json"
ASSET_KEYS = ("favicon", "favicon16", "favicon32", "icon192", "icon512", "appleTouchIcon")


def load_client_config(root: Path = ROOT) -> dict[str, Any]:
    path = root / "client.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"client.json: не удалось прочитать конфигурацию: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("client.json должен содержать JSON-объект")

    for field in ("name", "shortName", "description", "themeColor"):
        value = config.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"client.json: {field} должен быть непустой строкой")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", config["themeColor"]):
        raise ValueError("client.json: themeColor должен иметь формат #RRGGBB")

    assets = config.get("assets")
    if not isinstance(assets, dict):
        raise ValueError("client.json: assets должен быть JSON-объектом")
    for key in ASSET_KEYS:
        value = assets.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"client.json: assets.{key} должен быть непустым путём")
        asset_path = Path(value)
        if asset_path.is_absolute() or ".." in asset_path.parts or not value.startswith("client-assets/"):
            raise ValueError(f"client.json: assets.{key} должен находиться внутри client-assets/")
        resolved = (root / asset_path).resolve()
        assets_root = (root / "client-assets").resolve()
        if not resolved.is_relative_to(assets_root):
            raise ValueError(f"client.json: assets.{key} выходит за пределы client-assets/")
        if not resolved.is_file():
            raise ValueError(f"client.json: файл assets.{key} не найден: {value}")
    return config
