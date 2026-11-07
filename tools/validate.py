"""Проверка всех файлов дней: uv run tools/validate.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    CONTENT,
    DATA_VERSION,
    load_day_files,
    validate_day,
    validate_day_collection,
)


def main() -> int:
    try:
        days = load_day_files()
    except ValueError as exc:
        print(f"Ошибка данных: {exc}", file=sys.stderr)
        return 1

    errors = [error for day in days for error in validate_day(day)]
    try:
        meta = json.loads((CONTENT / "meta.json").read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            errors.append("content/meta.json должен содержать JSON-объект")
        elif meta.get("dataVersion") != DATA_VERSION:
            errors.append(
                f"content/meta.json: dataVersion должен быть {DATA_VERSION}, "
                f"получено {meta.get('dataVersion')!r}"
            )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"content/meta.json: не удалось прочитать конфигурацию: {exc}")
    if (Path(__file__).resolve().parent.parent / "client.json").exists():
        try:
            from client_config import load_client_config
            load_client_config()
        except ValueError as exc:
            errors.append(str(exc))
    errors.extend(validate_day_collection(days))
    for error in errors:
        print(" -", error)
    print(f"Проверено дней: {len(days)}, ошибок: {len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
