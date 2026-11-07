#!/usr/bin/env python3
"""Создание клиентской конфигурации без изменения файлов шаблона."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS_DIR = ROOT / "content" / "days"
TEMPLATE_VERSION_PATH = ROOT / "TEMPLATE_VERSION"
CLIENT_TEMPLATE_VERSION_PATH = ROOT / "CLIENT_TEMPLATE_VERSION"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import dump_json, write_text_atomic  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Подготовка шаблона под нового клиента")
    parser.add_argument("--name", required=True, help='например "Меню клиента"')
    parser.add_argument("--short-name", default=None, help="короткое имя под иконкой")
    parser.add_argument("--create-first-day", action="store_true", help="создать day-1.json")
    args = parser.parse_args(argv)

    name = args.name.strip()
    short = args.short_name.strip() if args.short_name else None
    if not name or (args.short_name is not None and not short):
        parser.error("--name и --short-name не должны быть пустыми")

    config_path = ROOT / "client.json"
    assets_created = False
    config_created = False
    try:
        if config_path.exists():
            raise FileExistsError("client.json уже существует — повторная инициализация запрещена")
        template_version = TEMPLATE_VERSION_PATH.read_text(encoding="utf-8").strip()
        if not template_version or "\n" in template_version or "\r" in template_version:
            raise ValueError("TEMPLATE_VERSION должен содержать одну непустую строку")
        config = {
            "name": name,
            "shortName": short or name,
            "description": "Меню питания: завтрак, обед, ужин и перекус на каждый день",
            "themeColor": "#2f7a4f",
            "assets": {
                "favicon": "client-assets/favicon.ico",
                "favicon16": "client-assets/favicon-16x16.png",
                "favicon32": "client-assets/favicon-32x32.png",
                "icon192": "client-assets/icon-192x192.png",
                "icon512": "client-assets/icon-512x512.png",
                "appleTouchIcon": "client-assets/apple-touch-icon.png"
            }
        }
        # Paths are populated with the client's own artwork after initialization.
        assets_dir = ROOT / "client-assets"
        if assets_dir.exists():
            raise FileExistsError("client-assets/ уже существует — проверьте состояние репозитория")
        staging_dir = ROOT / ".client-assets.tmp"
        if staging_dir.exists():
            raise FileExistsError("Найдена временная папка .client-assets.tmp — удалите её после проверки")
        staging_dir.mkdir()
        defaults = ROOT / "shared" / "assets" / "default"
        for asset in config["assets"].values():
            shutil.copy2(defaults / Path(asset).name, staging_dir / Path(asset).name)
        staging_dir.replace(assets_dir)
        assets_created = True
        write_text_atomic(config_path, dump_json(config))
        config_created = True
        if not CLIENT_TEMPLATE_VERSION_PATH.exists():
            write_text_atomic(CLIENT_TEMPLATE_VERSION_PATH, f"{template_version}\n")
        else:
            print("CLIENT_TEMPLATE_VERSION уже существует — сохраняю исходную версию")
    except (OSError, UnicodeError, ValueError, FileExistsError) as exc:
        if 'staging_dir' in locals():
            shutil.rmtree(staging_dir, ignore_errors=True)
        if assets_created:
            shutil.rmtree(assets_dir, ignore_errors=True)
        if config_created:
            config_path.unlink(missing_ok=True)
        print(f"Ошибка подготовки конфигурации клиента: {exc}", file=sys.stderr)
        return 1

    if args.create_first_day:
        day1 = DAYS_DIR / "day-1.json"
        if day1.exists():
            print("day-1.json уже существует — пропускаю создание")
        else:
            result = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "new_day.py"), "day-1", "--label", "1"],
                cwd=ROOT, check=False,
            )
            if result.returncode:
                config_path.unlink(missing_ok=True)
                shutil.rmtree(ROOT / "client-assets", ignore_errors=True)
                CLIENT_TEMPLATE_VERSION_PATH.unlink(missing_ok=True)
                print("Ошибка при создании day-1.json", file=sys.stderr)
                return result.returncode
            print("Создан content/days/day-1.json (шаблон)")

    print(f"Готово: {name}")
    print(f"  Конфигурация клиента: {config_path.relative_to(ROOT)}")
    print("  Персональные изображения: client-assets/")
    print(f"  Папка дней: {DAYS_DIR.relative_to(ROOT)}")
    print(f"  Исходная версия шаблона: {template_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
