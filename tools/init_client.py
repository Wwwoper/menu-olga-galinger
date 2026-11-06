#!/usr/bin/env python3
"""Инициализация шаблона под нового клиента."""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS_DIR = ROOT / "content" / "days"
TEMPLATE_VERSION_PATH = ROOT / "TEMPLATE_VERSION"
CLIENT_TEMPLATE_VERSION_PATH = ROOT / "CLIENT_TEMPLATE_VERSION"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import dump_json, write_text_atomic  # noqa: E402


def replace_once(
    source: str, pattern: str, replacement: Callable[[re.Match[str]], str], description: str
) -> str:
    result, count = re.subn(pattern, replacement, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Не удалось однозначно обновить {description}: найдено совпадений {count}")
    return result


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

    meta_path = ROOT / "content" / "meta.json"
    manifest_path = ROOT / "manifest.json"
    index_path = ROOT / "index.html"
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        html_text = index_path.read_text(encoding="utf-8")
        template_version = TEMPLATE_VERSION_PATH.read_text(encoding="utf-8").strip()
        if not template_version or "\n" in template_version or "\r" in template_version:
            raise ValueError("TEMPLATE_VERSION должен содержать одну непустую строку")
        if not isinstance(meta, dict) or not isinstance(manifest, dict):
            raise ValueError("meta.json и manifest.json должны содержать JSON-объекты")

        meta["title"] = name
        manifest["name"] = name
        if short is not None:
            manifest["short_name"] = short

        safe_name = html.escape(name, quote=True)
        sidebar_label = html.escape(short or "Меню", quote=True)
        apple_title = html.escape(short or "Меню", quote=True)
        html_text = replace_once(
            html_text, r"<title>.*?</title>",
            lambda _match: f"<title>{safe_name}</title>", "title страницы",
        )
        html_text = replace_once(
            html_text, r'(<div id="top-header">\s*<h1>).*?(</h1>)',
            lambda match: match.group(1) + safe_name + match.group(2), "заголовок шапки",
        )
        html_text = replace_once(
            html_text,
            r'(<nav id="sidebar"[^>]*>\s*<h1>).*?(</h1>)',
            lambda match: match.group(1) + sidebar_label + match.group(2),
            "заголовок боковой панели",
        )
        html_text = replace_once(
            html_text,
            r'(<div id="top-header">.*?<p>).*?(</p>)',
            lambda match: (
                match.group(1)
                + "Полное меню · Завтрак, обед, ужин и перекус для каждого дня"
                + match.group(2)
            ),
            "подзаголовок шапки",
        )
        html_text = replace_once(
            html_text, r'(<meta name="apple-mobile-web-app-title" content=").*?(">)',
            lambda match: match.group(1) + apple_title + match.group(2),
            "apple-mobile-web-app-title",
        )
        html_text = replace_once(
            html_text,
            r'(<span id="mobile-current-day"[^>]*>).*?(</span>)',
            lambda match: match.group(1) + sidebar_label + match.group(2),
            "подпись мобильной навигации",
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print(f"Ошибка подготовки конфигурации клиента: {exc}", file=sys.stderr)
        return 1

    # Все преобразования и проверки выполняются до первой записи.
    try:
        write_text_atomic(meta_path, dump_json(meta))
        write_text_atomic(manifest_path, dump_json(manifest))
        write_text_atomic(index_path, html_text)
        if not CLIENT_TEMPLATE_VERSION_PATH.exists():
            write_text_atomic(CLIENT_TEMPLATE_VERSION_PATH, f"{template_version}\n")
        else:
            print("CLIENT_TEMPLATE_VERSION уже существует — сохраняю исходную версию")
    except OSError as exc:
        print(f"Ошибка записи конфигурации: {exc}", file=sys.stderr)
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
                print("Ошибка при создании day-1.json", file=sys.stderr)
                return result.returncode
            print("Создан content/days/day-1.json (шаблон)")

    sw_path = ROOT / "service-worker.js"
    if sw_path.exists():
        sw = sw_path.read_text(encoding="utf-8")
        match = re.search(r"VERSION\s*=\s*['\"]([^'\"]+)['\"]", sw)
        if match:
            print(f"Не забудьте увеличить VERSION в service-worker.js (сейчас {match.group(1)})")

    print(f"Готово: {name}")
    if short:
        print(f"  short_name / apple-title: {short}")
    print(f"  Папка дней: {DAYS_DIR.relative_to(ROOT)}")
    print(f"  Исходная версия шаблона: {template_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
