"""Генерация content/days.json.

  uv run tools/build_index.py           # пересобрать индекс
  uv run tools/build_index.py --check   # код 1, если индекс устарел
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    INDEX_FILE,
    build_index,
    dump_json,
    load_day_files,
    validate_day,
    validate_day_collection,
    write_text_atomic,
)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    try:
        days = load_day_files()
    except ValueError as exc:
        print(f"Ошибка данных: {exc}", file=sys.stderr)
        return 1

    errors = [error for day in days for error in validate_day(day)]
    errors.extend(validate_day_collection(days))
    if errors:
        print("Ошибки в данных:")
        for error in errors:
            print(" -", error)
        return 1

    try:
        text = dump_json(build_index(days))
    except (KeyError, TypeError, ValueError) as exc:
        print("Ошибка индекса:", exc)
        return 1

    try:
        current = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else None
    except (OSError, UnicodeError) as exc:
        print(f"Не удалось прочитать {INDEX_FILE}: {exc}", file=sys.stderr)
        return 1

    if check:
        if current != text:
            print("content/days.json устарел. Запустите: uv run tools/build_index.py")
            return 1
        print("Индекс актуален")
        return 0

    if current == text:
        print("Индекс не изменился")
    else:
        try:
            write_text_atomic(INDEX_FILE, text)
        except OSError as exc:
            print(f"Не удалось записать {INDEX_FILE}: {exc}", file=sys.stderr)
            return 1
        print(f"Записан {INDEX_FILE.name}: {len(days)} дней")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
