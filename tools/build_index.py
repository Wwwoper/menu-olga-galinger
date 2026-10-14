"""Генерация content/days.json.

  uv run tools/build_index.py           # пересобрать индекс
  uv run tools/build_index.py --check   # код 1, если индекс устарел (для CI)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import INDEX_FILE, build_index, dump_json, load_day_files, validate_day  # noqa: E402


def main(argv: list[str]) -> int:
    check = "--check" in argv
    days = load_day_files()
    errors = [e for d in days for e in validate_day(d)]
    if errors:
        print("Ошибки в данных:")
        for e in errors:
            print(" -", e)
        return 1
    try:
        text = dump_json(build_index(days))
    except ValueError as exc:
        print("Ошибка индекса:", exc)
        return 1
    current = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else None
    if check:
        if current != text:
            print("content/days.json устарел. Запустите: uv run tools/build_index.py")
            return 1
        print("Индекс актуален")
        return 0
    if current == text:
        print("Индекс не изменился")
    else:
        INDEX_FILE.write_text(text, encoding="utf-8")
        print(f"Записан {INDEX_FILE.name}: {len(days)} дней")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
