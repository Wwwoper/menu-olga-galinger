"""Создание нового дня без частично записанных файлов.

  uv run tools/new_day.py day-45 --label 45
  uv run tools/new_day.py day-45 --label 45 --copy-from day-44
  uv run tools/new_day.py day-33-var-3 --label "33 (3)" --copy-from day-33
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    DAYS_DIR,
    INDEX_FILE,
    ID_RE,
    build_index,
    dump_json,
    load_day_files,
    parse_id,
    validate_day,
    validate_day_collection,
    write_text_atomic,
)

TEMPLATE_MEALS = [
    {"type": meal_type, "dish": None, "ingredients": [{"name": "Ингредиент", "grams": 100}]}
    for meal_type in ("breakfast", "lunch", "dinner", "snack")
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Создание JSON-файла дня меню")
    parser.add_argument("id", help="идентификатор вида day-N или day-N-var-M")
    parser.add_argument("--label", required=True)
    parser.add_argument("--copy-from")
    args = parser.parse_args(argv)

    if not isinstance(args.label, str) or not args.label.strip():
        print("label должен быть непустой строкой", file=sys.stderr)
        return 1
    if not ID_RE.fullmatch(args.id):
        print("id должен быть вида day-N или day-N-var-M")
        return 1

    target = DAYS_DIR / f"{args.id}.json"
    if target.exists():
        print(f"{target.name} уже существует")
        return 1

    number, variant = parse_id(args.id)
    try:
        existing_days = load_day_files(DAYS_DIR)
    except ValueError as exc:
        print(f"Ошибка данных: {exc}", file=sys.stderr)
        return 1
    existing_errors = [error for day in existing_days for error in validate_day(day)]
    existing_errors.extend(validate_day_collection(existing_days))
    if existing_errors:
        print("Существующие данные содержат ошибки:", file=sys.stderr)
        for error in existing_errors:
            print(" -", error, file=sys.stderr)
        return 1

    existing_by_id = {day["id"]: day for day in existing_days}
    parent_id = f"day-{number}"
    if variant and parent_id not in existing_by_id:
        print(f"Нельзя создать вариант: отсутствует основной день {parent_id}")
        return 1

    if args.copy_from:
        source = existing_by_id.get(args.copy_from)
        if source is None:
            print(f"Нет корректного дня {args.copy_from!r} для копирования")
            return 1
        meals = source["meals"]
    else:
        meals = TEMPLATE_MEALS

    day = {
        "id": args.id,
        "label": args.label.strip(),
        "variantOf": parent_id if variant else None,
        "meals": meals,
    }
    day_errors = validate_day(day)
    if day_errors:
        print("Не удалось сформировать день:", file=sys.stderr)
        for error in day_errors:
            print(" -", error, file=sys.stderr)
        return 1

    updated_days = [*existing_days, day]
    try:
        index_text = dump_json(build_index(updated_days))
    except (KeyError, TypeError, ValueError) as exc:
        print(f"Не удалось сформировать индекс: {exc}", file=sys.stderr)
        return 1

    # Сначала атомарно записываем день, затем индекс. При ошибке индекса старый
    # индекс остаётся целым, а новый день можно удалить/повторно обработать.
    target_created = False
    try:
        write_text_atomic(target, dump_json(day))
        target_created = True
        write_text_atomic(INDEX_FILE, index_text)
    except OSError as exc:
        print(f"Ошибка записи файлов: {exc}", file=sys.stderr)
        if target_created:
            try:
                target.unlink(missing_ok=True)
            except OSError as cleanup_error:
                print(f"Не удалось удалить частично созданный день: {cleanup_error}", file=sys.stderr)
        return 1

    print(f"Создан {target}")
    print(f"Обновлён {INDEX_FILE.name}: {len(updated_days)} дней")
    return 0


if __name__ == "__main__":
    sys.exit(main())
