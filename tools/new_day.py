"""Создание нового дня.

  uv run tools/new_day.py day-45 --label 45
  uv run tools/new_day.py day-45 --label 45 --copy-from day-44
  uv run tools/new_day.py day-33-var-3 --label "33 (3)" --copy-from day-33
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DAYS_DIR, ID_RE, dump_json, parse_id  # noqa: E402

TEMPLATE_MEALS = [
    {"type": t, "dish": None, "ingredients": [{"name": "Ингредиент", "grams": 100}]}
    for t in ("breakfast", "lunch", "dinner", "snack")
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("id")
    ap.add_argument("--label", required=True)
    ap.add_argument("--copy-from")
    args = ap.parse_args()

    if not ID_RE.match(args.id):
        print("id должен быть вида day-N или day-N-var-M")
        return 1
    target = DAYS_DIR / f"{args.id}.json"
    if target.exists():
        print(f"{target.name} уже существует")
        return 1
    num, var = parse_id(args.id)
    if args.copy_from:
        src = DAYS_DIR / f"{args.copy_from}.json"
        if not src.exists():
            print(f"Нет файла {src.name}")
            return 1
        meals = json.loads(src.read_text(encoding="utf-8"))["meals"]
    else:
        meals = TEMPLATE_MEALS
    day = {"id": args.id, "label": args.label, "variantOf": f"day-{num}" if var else None, "meals": meals}
    target.write_text(dump_json(day), encoding="utf-8")
    print(f"Создан {target}")
    root = Path(__file__).resolve().parent
    return subprocess.call([sys.executable, str(root / "build_index.py")])


if __name__ == "__main__":
    sys.exit(main())
