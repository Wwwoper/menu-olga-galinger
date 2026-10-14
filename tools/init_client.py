#!/usr/bin/env python3
"""Инициализация шаблона под нового клиента.

uv run tools/init_client.py --name "Меню Анны Ивановой"
uv run tools/init_client.py --name "Меню Анны Ивановой" --short-name "Анна"
uv run tools/init_client.py --name "Меню Анны Ивановой" --create-first-day
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS_DIR = ROOT / "content" / "days"


def write_json(path: Path, data: dict) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    p = argparse.ArgumentParser(description="Подготовка шаблона под нового клиента")
    p.add_argument("--name", required=True, help='например "Меню Анны Ивановой"')
    p.add_argument(
        "--short-name",
        default=None,
        help='короткое имя под иконкой (по умолчанию не меняется, обычно "Меню")',
    )
    p.add_argument(
        "--create-first-day",
        action="store_true",
        help="создать day-1.json с пустым шаблоном (завтрак/обед/ужин/перекус)",
    )
    args = p.parse_args()
    name = args.name.strip()
    short = args.short_name.strip() if args.short_name else None

    # Убедиться, что папка дней существует
    DAYS_DIR.mkdir(parents=True, exist_ok=True)

    # content/meta.json
    meta_path = ROOT / "content" / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["title"] = name
    write_json(meta_path, meta)

    # manifest.json
    man_path = ROOT / "manifest.json"
    man = json.loads(man_path.read_text(encoding="utf-8"))
    man["name"] = name
    if short is not None:
        man["short_name"] = short
    write_json(man_path, man)

    # index.html — title, top-header h1, sidebar h1, subtitle, apple-title
    idx_path = ROOT / "index.html"
    html = idx_path.read_text(encoding="utf-8")

    html = re.sub(
        r"(<title>).*?(</title>)",
        lambda m: f"{m.group(1)}{name}{m.group(2)}",
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(<div id="top-header">\s*<h1>).*?(</h1>)',
        lambda m: f"{m.group(1)}{name}{m.group(2)}",
        html,
        count=1,
        flags=re.S,
    )
    sidebar_label = short or "Меню"
    html = re.sub(
        r'(<nav id="sidebar"[^>]*>\s*<h1>).*?(<button)',
        lambda m: f"{m.group(1)}{sidebar_label} {m.group(2)}",
        html,
        count=1,
        flags=re.S,
    )
    html = re.sub(
        r'(<div id="top-header">.*?<p>).*?(</p>)',
        lambda m: (
            f"{m.group(1)}Полное меню · Завтрак, обед, ужин и перекус для каждого дня"
            f"{m.group(2)}"
        ),
        html,
        count=1,
        flags=re.S,
    )
    apple_title = short or "Меню"
    html = re.sub(
        r'(<meta name="apple-mobile-web-app-title" content=").*?(")',
        lambda m: f"{m.group(1)}{apple_title}{m.group(2)}",
        html,
        count=1,
    )
    html = re.sub(
        r'(<span id="mobile-current-day"[^>]*>).*?(</span>)',
        lambda m: f"{m.group(1)}{sidebar_label}{m.group(2)}",
        html,
        count=1,
        flags=re.S,
    )

    idx_path.write_text(html, encoding="utf-8")

    # Опционально создать первый день
    if args.create_first_day:
        day1 = DAYS_DIR / "day-1.json"
        if day1.exists():
            print("  day-1.json уже существует — пропускаю создание")
        else:
            rc = subprocess.call(
                [
                    sys.executable,
                    str(ROOT / "tools" / "new_day.py"),
                    "day-1",
                    "--label",
                    "1",
                ]
            )
            if rc != 0:
                print("Ошибка при создании day-1.json", file=sys.stderr)
                sys.exit(rc)
            print("  Создан content/days/day-1.json (пустой шаблон)")

    sw_path = ROOT / "service-worker.js"
    if sw_path.exists():
        sw = sw_path.read_text(encoding="utf-8")
        m = re.search(r"VERSION\s*=\s*['\"]([^'\"]+)['\"]", sw)
        if m:
            print(
                f"Не забудьте увеличить VERSION в service-worker.js (сейчас {m.group(1)})"
            )

    print(f"Готово: {name}")
    if short:
        print(f"  short_name / apple-title: {short}")
    print(f"  Папка дней: {DAYS_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
