"""Проверка всех файлов дней:  uv run tools/validate.py"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import load_day_files, validate_day  # noqa: E402


def main() -> int:
    days = load_day_files()
    errors = [e for d in days for e in validate_day(d)]
    ids = [d.get("id") for d in days]
    errors += [f"дубль id {i}" for i in set(ids) if ids.count(i) > 1]
    for e in errors:
        print(" -", e)
    print(f"Проверено дней: {len(days)}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
