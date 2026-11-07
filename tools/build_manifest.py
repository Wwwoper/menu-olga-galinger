#!/usr/bin/env python3
"""Генерирует web app manifest из конфигурации клиента."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from client_config import load_client_config  # noqa: E402
from common import dump_json, write_text_atomic  # noqa: E402


def build_manifest(config: dict) -> dict:
    assets = config["assets"]
    return {
        "name": config["name"],
        "short_name": config["shortName"],
        "description": config["description"],
        "lang": "ru",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#faf9f7",
        "theme_color": config["themeColor"],
        "icons": [
            {"src": assets["icon192"], "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": assets["icon512"], "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": assets["icon512"], "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


def main() -> int:
    try:
        config = load_client_config()
        write_text_atomic(ROOT / "manifest.json", dump_json(build_manifest(config)))
    except (OSError, ValueError) as exc:
        print(f"Ошибка сборки manifest.json: {exc}", file=sys.stderr)
        return 1
    print("Создан manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
