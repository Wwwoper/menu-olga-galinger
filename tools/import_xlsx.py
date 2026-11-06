"""Extract a client's daily menus from an .xlsx workbook into JSON files.

The parser uses only Python's standard library. It reads the XLSX package
(OOXML) directly, so it does not depend on openpyxl, pandas, or Excel itself.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
import zipfile
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": DOC_REL_NS, "pr": PKG_REL_NS}

MEAL_HEADER_RE = re.compile(
    r"^\s*(второй\s+завтрак|завтрак|обед|ужин|перекус|полдник)\b(.*)$",
    re.IGNORECASE,
)
MENU_NUMBER_RE = re.compile(r"меню\s*(\d+)(?![\d.])", re.IGNORECASE)
VARIANT_NUMBER_RE = re.compile(r"(\d+)\s*вариант|вариант\s*(\d+)", re.IGNORECASE)

MEAL_TYPES = {
    "завтрак": "breakfast",
    "второй завтрак": "snack",
    "обед": "lunch",
    "ужин": "dinner",
    "перекус": "snack",
    "полдник": "snack",
}


@dataclass(frozen=True)
class Sheet:
    name: str
    path: str


@dataclass
class ParsedSheet:
    name: str
    rows: dict[int, dict[int, Any]]


def normalize_text(value: Any) -> str:
    """Collapse whitespace and case-fold a value for reliable name matching."""
    return " ".join(str(value or "").split()).casefold()


def column_number(cell_ref: str) -> int:
    """Convert an Excel column reference (e.g. AF) to a 1-based number."""
    letters = re.match(r"[A-Z]+", cell_ref.upper())
    if not letters:
        raise ValueError(f"Invalid Excel cell reference: {cell_ref!r}")
    result = 0
    for letter in letters.group(0):
        result = result * 26 + ord(letter) - ord("A") + 1
    return result


def parse_numeric(value: Any) -> Decimal | None:
    """Return a Decimal for numeric Excel values, otherwise None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def round_grams(value: Any) -> int | float | None:
    """Round weights to a whole gram, like the example JSON."""
    number = parse_numeric(value)
    if number is None:
        return None
    rounded = number.quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return int(rounded)


def read_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    """Read xl/sharedStrings.xml, including rich-text runs."""
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []

    root = ET.fromstring(archive.read(path))
    result: list[str] = []
    for item in root.findall("m:si", NS):
        result.append("".join(node.text or "" for node in item.findall(".//m:t", NS)))
    return result


def read_workbook_sheets(archive: zipfile.ZipFile) -> list[Sheet]:
    """Resolve worksheet names to XML paths from workbook relationships."""
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        relation.attrib["Id"]: relation.attrib["Target"]
        for relation in relationships.findall("pr:Relationship", NS)
    }

    sheets: list[Sheet] = []
    for item in workbook.findall("m:sheets/m:sheet", NS):
        relation_id = item.attrib.get(f"{{{DOC_REL_NS}}}id")
        target = rel_targets.get(relation_id or "")
        if not target:
            continue

        if target.startswith("/"):
            xml_path = target.lstrip("/")
        else:
            xml_path = posixpath.normpath(posixpath.join("xl", target))

        # Skip chart sheets or other non-worksheet entries, if present.
        if xml_path.startswith("xl/worksheets/"):
            sheets.append(Sheet(name=item.attrib["name"], path=xml_path))
    return sheets


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    """Read a cached cell value. Formula cells use their cached <v> result."""
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(".//m:t", NS))

    value_node = cell.find("m:v", NS)
    if value_node is None or value_node.text is None:
        return None
    raw = value_node.text

    if cell_type == "s":
        try:
            return shared_strings[int(raw)]
        except (ValueError, IndexError):
            return raw
    if cell_type in {"str", "e"}:
        return raw
    if cell_type == "b":
        return raw == "1"

    # Ordinary numeric cells have no type attribute. Preserve integers as ints.
    try:
        number = Decimal(raw)
        if number == number.to_integral_value():
            return int(number)
        return float(number)
    except (InvalidOperation, ValueError):
        return raw


def read_worksheet(
    archive: zipfile.ZipFile,
    sheet: Sheet,
    shared_strings: list[str],
) -> ParsedSheet:
    """Read worksheet data into {row_number: {column_number: value}}."""
    root = ET.fromstring(archive.read(sheet.path))
    rows: dict[int, dict[int, Any]] = {}

    sheet_data = root.find("m:sheetData", NS)
    if sheet_data is None:
        return ParsedSheet(name=sheet.name, rows=rows)

    for row_node in sheet_data.findall("m:row", NS):
        row_number = int(row_node.attrib["r"])
        values: dict[int, Any] = {}
        for cell in row_node.findall("m:c", NS):
            ref = cell.attrib.get("r")
            if not ref:
                continue
            value = cell_value(cell, shared_strings)
            if value is not None:
                values[column_number(ref)] = value
        rows[row_number] = values

    return ParsedSheet(name=sheet.name, rows=rows)


def find_client_column(rows: dict[int, dict[int, Any]], client_name: str) -> int | None:
    """Find the column that contains the client name in the first row."""
    wanted = normalize_text(client_name)
    header = rows.get(1, {})
    matches = [
        column for column, value in header.items() if normalize_text(value) == wanted
    ]
    if len(matches) > 1:
        raise ValueError(
            f"В строке 1 найдено несколько столбцов для клиента {client_name!r}: {matches}"
        )
    return matches[0] if matches else None


def parse_meal_header(text: str) -> tuple[str, str | None] | None:
    """Return (JSON meal type, dish/heading) for a meal heading row."""
    match = MEAL_HEADER_RE.match(text)
    if not match:
        return None

    source_type = " ".join(match.group(1).casefold().split())
    meal_type = MEAL_TYPES[source_type]
    dish = match.group(2).strip().strip(" :—–-\t")
    dish = re.sub(r"^готовим\b\s*", "", dish, flags=re.IGNORECASE).strip()
    dish = dish or None

    # Avoid treating connectors like "Ужин и перекус" as a dish name.
    if dish and re.match(r"^(?:и|или)\b", dish, flags=re.IGNORECASE):
        dish = None

    return meal_type, dish


def capitalize_first(text: str) -> str:
    """Capitalize just the first character, preserving the original wording."""
    return text[:1].upper() + text[1:] if text else text


HTML_CHARS_RE = re.compile(r"[<>]")


def clean_name(text: str) -> str:
    """Убрать < и >, схлопнуть пробелы и срезать хвостовую пунктуацию."""
    text = HTML_CHARS_RE.sub("", text)
    return " ".join(text.split()).strip(" ,;:")


def extract_meals(sheet: ParsedSheet, client_column: int) -> list[dict[str, Any]]:
    """Extract meal sections and ingredient grams from one matching worksheet."""
    meals: list[dict[str, Any]] = []
    meals_by_type: dict[str, dict[str, Any]] = {}
    current_meal: dict[str, Any] | None = None

    for row_number in sorted(sheet.rows):
        row = sheet.rows[row_number]
        ingredient_name = row.get(1)
        if not isinstance(ingredient_name, str):
            continue

        ingredient_name = clean_name(ingredient_name)
        if not ingredient_name:
            continue

        parsed_header = parse_meal_header(ingredient_name)
        if parsed_header:
            meal_type, dish = parsed_header
            dish = clean_name(dish) or None if dish else None
            current_meal = meals_by_type.get(meal_type)
            if current_meal is None:
                current_meal = {"type": meal_type, "dish": dish, "ingredients": []}
                meals_by_type[meal_type] = current_meal
                meals.append(current_meal)
            else:
                print(
                    f"Предупреждение: лист {sheet.name!r}: повторный тип "
                    f"{meal_type!r}, приёмы пищи объединены.",
                    file=sys.stderr,
                )
                current_meal["dish"] = current_meal["dish"] or dish
            continue

        if current_meal is None:
            continue

        grams = round_grams(row.get(client_column))
        if grams is None or grams <= 0:
            continue

        current_meal["ingredients"].append(
            {"name": capitalize_first(ingredient_name), "grams": grams}
        )

    return [meal for meal in meals if meal["ingredients"]]


def make_day_identity(
    sheet_name: str, fallback_number: int
) -> tuple[str, str, str | None]:
    """Return (id, label, variantOf) based on names like 'меню 33 (2вариант)'."""
    number_match = MENU_NUMBER_RE.search(sheet_name)
    day_number = number_match.group(1) if number_match else str(fallback_number)
    base_id = f"day-{day_number}"

    variant_match = VARIANT_NUMBER_RE.search(sheet_name)
    has_variant = variant_match is not None or "вариант" in sheet_name.casefold()
    if has_variant:
        variant_number = "2"
        if variant_match:
            variant_number = variant_match.group(1) or variant_match.group(2) or "2"
        return (
            f"{base_id}-var-{variant_number}",
            f"{day_number} {variant_number})",
            base_id,
        )

    return base_id, day_number, None


def fallback_start_number(sheets: list[Sheet]) -> int:
    """Start generated IDs after every explicit numeric menu ID in the workbook."""
    explicit_numbers = [
        int(match.group(1))
        for sheet in sheets
        if (match := MENU_NUMBER_RE.search(sheet.name)) is not None
    ]
    return max(explicit_numbers, default=0) + 1


def select_sheets(sheets: list[Sheet], sheet_name: str | None) -> list[Sheet]:
    """Return all sheets or only the requested sheet, matched by normalized name."""
    if not sheet_name:
        return sheets

    wanted = normalize_text(sheet_name)
    matching_sheets = [
        sheet for sheet in sheets if normalize_text(sheet.name) == wanted
    ]
    if not matching_sheets:
        raise ValueError(
            f"Лист {sheet_name!r} не найден в книге. Проверьте его название."
        )
    return matching_sheets


def extract_client_menus(
    input_path: Path,
    client_name: str,
    sheet_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return JSON-ready day objects, optionally limited to one worksheet."""
    if not input_path.exists():
        raise FileNotFoundError(f"Excel-файл не найден: {input_path}")
    if input_path.suffix.lower() != ".xlsx":
        raise ValueError("Поддерживается формат .xlsx")

    days: list[dict[str, Any]] = []
    source_sheets: list[str] = []
    with zipfile.ZipFile(input_path) as archive:
        shared_strings = read_shared_strings(archive)
        sheets = read_workbook_sheets(archive)
        sheets = select_sheets(sheets, sheet_name)
        fallback_number = fallback_start_number(sheets)

        for sheet in sheets:
            parsed_sheet = read_worksheet(archive, sheet, shared_strings)
            client_column = find_client_column(parsed_sheet.rows, client_name)
            if client_column is None:
                continue

            uses_fallback_number = MENU_NUMBER_RE.search(sheet.name) is None
            day_id, label, variant_of = make_day_identity(sheet.name, fallback_number)
            meals = extract_meals(parsed_sheet, client_column)
            if not meals:
                print(
                    f"Предупреждение: лист {sheet.name!r} содержит клиента, "
                    "но блюда не найдены.",
                    file=sys.stderr,
                )
                continue

            days.append(
                {
                    "id": day_id,
                    "label": label,
                    "variantOf": variant_of,
                    "meals": meals,
                }
            )
            source_sheets.append(sheet.name)
            if uses_fallback_number:
                fallback_number += 1

    # Avoid silently overwriting two sheets that map to the same day id.
    sources_by_id: dict[str, list[str]] = {}
    for day, sheet_name in zip(days, source_sheets, strict=True):
        sources_by_id.setdefault(day["id"], []).append(sheet_name)
    duplicates = {
        day_id: names for day_id, names in sources_by_id.items() if len(names) > 1
    }
    if duplicates:
        details = "; ".join(
            f"{day_id}: " + ", ".join(repr(name) for name in names)
            for day_id, names in sorted(duplicates.items())
        )
        raise ValueError("Несколько листов получили одинаковые id: " + details)
    return days


def write_json_files(days: list[dict[str, Any]], output_dir: Path) -> None:
    """Write one UTF-8 JSON file per day without overwriting existing files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = [output_dir / f"{day['id']}.json" for day in days]
    existing = [path.name for path in targets if path.exists()]
    if existing:
        raise FileExistsError(
            "Отказ от перезаписи существующих файлов: " + ", ".join(existing)
        )

    written: list[Path] = []
    try:
        for day, output_path in zip(days, targets, strict=True):
            with output_path.open("x", encoding="utf-8", newline="\n") as file:
                written.append(output_path)
                json.dump(day, file, ensure_ascii=False, indent=2)
                file.write("\n")
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Извлечь меню клиента из Excel и сохранить по одному JSON на лист."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Путь к исходному файлу .xlsx",
    )
    parser.add_argument(
        "--client",
        default="Клиент",
        help="Имя клиента в первой строке листа (по умолчанию: Клиент)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Папка для JSON-файлов (по умолчанию: ./output)",
    )
    parser.add_argument(
        "--sheet",
        help=(
            "Название одного листа Excel для обработки; если не указано, "
            "обрабатываются все листы. Регистр и лишние пробелы не учитываются."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        days = extract_client_menus(
            args.input.expanduser(),
            args.client,
            sheet_name=args.sheet,
        )
        if not days:
            if args.sheet:
                message = (
                    f"На листе {args.sheet!r} не найден клиент {args.client!r} "
                    "или не удалось извлечь блюда. Проверьте имя клиента и содержимое листа."
                )
            else:
                message = (
                    f"Листы с клиентом {args.client!r} не найдены. "
                    "Проверьте имя и исходный файл."
                )
            print(message, file=sys.stderr)
            return 1

        output_dir = args.output.expanduser()
        write_json_files(days, output_dir)

        total_meals = sum(len(day["meals"]) for day in days)
        total_ingredients = sum(
            len(meal["ingredients"]) for day in days for meal in day["meals"]
        )
        print(f"Клиент: {args.client}")
        print(f"Создано дней: {len(days)}")
        print(f"Приёмов пищи: {total_meals}")
        print(f"Ингредиентов: {total_ingredients}")
        print(f"Папка результата: {output_dir.resolve()}")
        print("Файлы:")
        for day in days:
            print(f"  - {day['id']}.json ({len(day['meals'])} приёмов пищи)")
        return 0
    except (OSError, zipfile.BadZipFile, ET.ParseError, KeyError, ValueError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
