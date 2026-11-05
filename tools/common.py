"""Общие функции для tools/*.py (только стандартная библиотека)."""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DAYS_DIR = CONTENT / "days"
INDEX_FILE = CONTENT / "days.json"

DATA_VERSION = 1
MEAL_TYPES = ("breakfast", "lunch", "dinner", "snack")
ID_RE = re.compile(r"^day-(\d+)(?:-var-(\d+))?$")


def parse_id(day_id: str) -> tuple[int, int]:
    """day-33 -> (33, 0); day-33-var-2 -> (33, 2)."""
    match = ID_RE.fullmatch(day_id)
    if not match:
        raise ValueError(f"Некорректный id дня: {day_id!r}")
    return int(match.group(1)), int(match.group(2) or 0)


def sort_key(day_id: str) -> tuple[int, int]:
    return parse_id(day_id)


def normalize_search(text: str) -> str:
    """Одинаково нормализует текст для индекса: регистр, ё/е и разделители."""
    text = text.lower().replace("ё", "е")
    text = re.sub(r"[^\w–\-+]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def meal_index(day: dict[str, Any]) -> list[dict[str, Any]]:
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


def search_string(day: dict[str, Any]) -> str:
    num, var = parse_id(day["id"])
    if var:
        head = f"{day['label']} {num} вариант {var}"
    else:
        head = f"{day['label']} день {day['label']}"
    parts = [head]
    for meal in day["meals"]:
        if meal.get("dish"):
            parts.append(meal["dish"])
        parts.extend(ingredient["name"] for ingredient in meal["ingredients"])
    return normalize_search(" ".join(parts))


def dump_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def write_text_atomic(path: Path, text: str) -> None:
    """Записывает файл через временный файл в том же каталоге и os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_name = temp.name
            temp.write(text)
            temp.flush()
        Path(temp_name).replace(path)
    finally:
        if temp_name and Path(temp_name).exists():
            Path(temp_name).unlink()


def load_day_files(days_dir: Path = DAYS_DIR) -> list[dict[str, Any]]:
    days: list[dict[str, Any]] = []
    if not days_dir.exists():
        return days
    for path in sorted(days_dir.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path.name}: не удалось прочитать JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: корневое значение JSON должно быть объектом")
        data["_path"] = path
        days.append(data)
    return days


def validate_day(day: Any) -> list[str]:
    """Возвращает ошибки структуры дня, не падая на произвольном JSON."""
    if not isinstance(day, dict):
        return [f"день должен быть JSON-объектом, получено {type(day).__name__}"]

    path = day.get("_path")
    where = path.name if isinstance(path, Path) else day.get("id", "?")
    errors: list[str] = []

    def err(message: str) -> None:
        errors.append(f"{where}: {message}")

    day_id = day.get("id")
    parsed_id: tuple[int, int] | None = None
    if not isinstance(day_id, str):
        err(f"id должен быть строкой, получено {day_id!r}")
    else:
        try:
            parsed_id = parse_id(day_id)
        except ValueError:
            err(f"id {day_id!r} не соответствует day-N или day-N-var-M")
    if isinstance(path, Path) and isinstance(day_id, str) and path.stem != day_id:
        err(f"id {day_id!r} не совпадает с именем файла {path.name!r}")

    label = day.get("label")
    if not isinstance(label, str) or not label.strip():
        err("label должен быть непустой строкой")

    variant_of = day.get("variantOf")
    if variant_of is not None and not isinstance(variant_of, str):
        err("variantOf должен быть строкой или null")
    if parsed_id:
        number, variant = parsed_id
        expected_parent = f"day-{number}" if variant else None
        if variant and variant_of != expected_parent:
            err(f"вариант {day_id} должен иметь variantOf={expected_parent!r}")
        elif not variant and variant_of is not None:
            err("основной день не должен иметь variantOf")

    meals = day.get("meals")
    if not isinstance(meals, list) or not meals:
        err("meals должен быть непустым списком")
        return errors

    seen: set[str] = set()
    for meal_index_, meal in enumerate(meals):
        meal_path = f"meals[{meal_index_}]"
        if not isinstance(meal, dict):
            err(f"{meal_path} должен быть объектом")
            continue

        meal_type = meal.get("type")
        if not isinstance(meal_type, str) or meal_type not in MEAL_TYPES:
            err(f"{meal_path}.type {meal_type!r} не из {MEAL_TYPES}")
        elif meal_type in seen:
            err(f"{meal_path}.type {meal_type!r} повторяется")
        else:
            seen.add(meal_type)

        dish = meal.get("dish")
        if dish is not None and (not isinstance(dish, str) or not dish.strip()):
            err(f"{meal_path}.dish должен быть непустой строкой или null")

        ingredients = meal.get("ingredients")
        if not isinstance(ingredients, list) or not ingredients:
            err(f"{meal_path}.ingredients должен быть непустым списком")
            continue
        for ingredient_index, ingredient in enumerate(ingredients):
            ingredient_path = f"{meal_path}.ingredients[{ingredient_index}]"
            if not isinstance(ingredient, dict):
                err(f"{ingredient_path} должен быть объектом")
                continue
            name = ingredient.get("name")
            if not isinstance(name, str) or not name.strip():
                err(f"{ingredient_path}.name должен быть непустой строкой")
            elif "<" in name or ">" in name:
                err(f"{ingredient_path}.name содержит HTML-символы")
            grams = ingredient.get("grams")
            if not isinstance(grams, int) or isinstance(grams, bool) or grams <= 0:
                err(
                    f"{ingredient_path}.grams должен быть целым числом > 0, "
                    f"получено {grams!r}"
                )
    return errors


def validate_day_collection(days: list[Any]) -> list[str]:
    """Проверяет уникальность ID и корректность ссылок вариантов на основные дни."""
    errors: list[str] = []
    ids = [day.get("id") for day in days if isinstance(day, dict)]
    duplicates = sorted(
        {day_id for day_id in ids if isinstance(day_id, str) and ids.count(day_id) > 1}
    )
    errors.extend(f"дубль id {day_id!r}" for day_id in duplicates)

    by_id = {
        day["id"]: day
        for day in days
        if isinstance(day, dict) and isinstance(day.get("id"), str)
    }
    for day in days:
        if not isinstance(day, dict):
            continue
        day_id = day.get("id")
        parent_id = day.get("variantOf")
        if parent_id is None:
            continue
        parent = by_id.get(parent_id) if isinstance(parent_id, str) else None
        if parent is None:
            errors.append(f"{day_id}: variantOf указывает на несуществующий {parent_id!r}")
        elif parent.get("variantOf") is not None:
            errors.append(
                f"{day_id}: variantOf {parent_id!r} должен указывать на основной день, "
                "а не на вариант"
            )
    return errors


def build_index(days: list[dict[str, Any]]) -> dict[str, Any]:
    days = sorted(days, key=lambda day: sort_key(day["id"]))
    collection_errors = validate_day_collection(days)
    if collection_errors:
        raise ValueError("; ".join(collection_errors))
    entries = [
        {
            "id": day["id"],
            "index": index,
            "label": day["label"],
            "file": f"days/{day['id']}.json",
            "search": search_string(day),
            "meals": meal_index(day),
        }
        for index, day in enumerate(days)
    ]
    main_days = sum(1 for day in days if not day.get("variantOf"))
    return {"mainDays": main_days, "total": len(days), "days": entries}
