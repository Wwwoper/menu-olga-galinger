"""Общие функции для tools/*.py (только стандартная библиотека)."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DAYS_DIR = CONTENT / "days"
INDEX_FILE = CONTENT / "days.json"

MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")
ID_RE = re.compile(r"^day-(\d+)(?:-var-(\d+))?$")


def parse_id(day_id: str) -> tuple[int, int]:
    """day-33 -> (33, 0); day-33-var-2 -> (33, 2)."""
    m = ID_RE.match(day_id)
    if not m:
        raise ValueError(f"Некорректный id дня: {day_id!r}")
    return int(m.group(1)), int(m.group(2) or 0)


def sort_key(day_id: str) -> tuple[int, int]:
    return parse_id(day_id)


def normalize_search(text: str) -> str:
    """Одинаково нормализует текст для индекса: регистр, ё/е и разделители."""
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w–\-+]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def meal_index(day: dict) -> list[dict]:
    """Строит поисковые записи приёмов пищи, сохраняя исходные названия."""
    meals = []
    for meal in day["meals"]:
        dish = meal.get("dish")
        meals.append(
            {
                "t": meal["type"],
                "d": normalize_search(dish) if dish else None,
                "dn": dish,
                "i": [
                    {"s": normalize_search(ingredient["name"]), "n": ingredient["name"]}
                    for ingredient in meal["ingredients"]
                ],
            }
        )
    return meals


def search_string(day: dict) -> str:
    num, var = parse_id(day["id"])
    if var:
        head = f"{day['label']} {num} вариант {var}"
    else:
        head = f"{day['label']} день {day['label']}"
    parts = [head]
    for meal in day["meals"]:
        if meal.get("dish"):
            parts.append(meal["dish"])
        parts.extend(i["name"] for i in meal["ingredients"])
    return normalize_search(" ".join(parts))


def dump_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def load_day_files(days_dir: Path = DAYS_DIR) -> list[dict]:
    days = []
    for path in sorted(days_dir.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        data["_path"] = path
        days.append(data)
    return days


def validate_day(day: dict) -> list[str]:
    """Возвращает список ошибок (пустой список = день корректен)."""
    errors: list[str] = []
    path = day.get("_path")
    where = path.name if path else day.get("id", "?")

    def err(msg: str) -> None:
        errors.append(f"{where}: {msg}")

    day_id = day.get("id")
    if not isinstance(day_id, str) or not ID_RE.match(day_id):
        err(f"id {day_id!r} не соответствует day-N или day-N-var-M")
    elif path and path.stem != day_id:
        err(f"id {day_id!r} не совпадает с именем файла {path.name!r}")
    if not isinstance(day.get("label"), str) or not day["label"].strip():
        err("label должен быть непустой строкой")
    variant_of = day.get("variantOf")
    if variant_of is not None and not isinstance(variant_of, str):
        err("variantOf должен быть строкой или null")
    meals = day.get("meals")
    if not isinstance(meals, list) or not meals:
        err("meals должен быть непустым списком")
        return errors
    seen = set()
    for i, meal in enumerate(meals):
        m = f"meals[{i}]"
        mtype = meal.get("type")
        if mtype not in MEAL_TYPES:
            err(f"{m}.type {mtype!r} не из {MEAL_TYPES}")
        elif mtype in seen:
            err(f"{m}.type {mtype!r} повторяется")
        seen.add(mtype)
        dish = meal.get("dish")
        if dish is not None and (not isinstance(dish, str) or not dish.strip()):
            err(f"{m}.dish должен быть непустой строкой или null")
        ings = meal.get("ingredients")
        if not isinstance(ings, list) or not ings:
            err(f"{m}.ingredients должен быть непустым списком")
            continue
        for j, ing in enumerate(ings):
            p = f"{m}.ingredients[{j}]"
            name = ing.get("name")
            if not isinstance(name, str) or not name.strip():
                err(f"{p}.name пустой")
            elif "<" in name or ">" in name:
                err(f"{p}.name содержит HTML-символы")
            g = ing.get("grams")
            if not isinstance(g, int) or isinstance(g, bool) or g <= 0:
                err(f"{p}.grams должен быть целым числом > 0, получено {g!r}")
    return errors


def build_index(days: list[dict]) -> dict:
    days = sorted(days, key=lambda d: sort_key(d["id"]))
    ids = [d["id"] for d in days]
    if len(ids) != len(set(ids)):
        raise ValueError("Есть дубли id")
    for d in days:
        vo = d.get("variantOf")
        if vo is not None and vo not in ids:
            raise ValueError(f"{d['id']}: variantOf указывает на несуществующий {vo!r}")
    entries = [
        {
            "id": d["id"],
            "index": i,
            "label": d["label"],
            "file": f"days/{d['id']}.json",
            "search": search_string(d),
            "meals": meal_index(d),
        }
        for i, d in enumerate(days)
    ]
    main = sum(1 for d in days if not d.get("variantOf"))
    return {"mainDays": main, "total": len(days), "days": entries}
