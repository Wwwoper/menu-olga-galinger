"""Интерактивное создание клиента из локальной XLSX-книги.

Запуск: uv run tools/create_client.py
Исходная таблица после успешного импорта переносится в input/archive/.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "input"
ARCHIVE_DIR = INPUT_DIR / "archive"
DAYS_DIR = ROOT / "content" / "days"
INDEX_FILE = ROOT / "content" / "days.json"
CLIENT_TEMPLATE_VERSION_PATH = ROOT / "CLIENT_TEMPLATE_VERSION"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import import_xlsx  # noqa: E402
import init_client  # noqa: E402
from common import (  # noqa: E402
    build_index,
    dump_json,
    validate_day,
    validate_day_collection,
    write_text_atomic,
)


CONFIG_FILES = (
    ROOT / "client.json",
    CLIENT_TEMPLATE_VERSION_PATH,
    INDEX_FILE,
)


def discover_workbooks(input_dir: Path) -> list[Path]:
    """Return XLSX files placed directly in the input directory."""
    if not input_dir.is_dir():
        return []
    return sorted(
        (path for path in input_dir.iterdir() if path.is_file() and path.suffix.lower() == ".xlsx"),
        key=lambda path: path.name.casefold(),
    )


def choose_workbook(input_dir: Path, explicit_path: Path | None = None) -> Path:
    if explicit_path is not None:
        path = explicit_path.expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Excel-файл не найден: {path}")
        if path.suffix.lower() != ".xlsx":
            raise ValueError("Поддерживается только формат .xlsx")
        return path

    workbooks = discover_workbooks(input_dir)
    if not workbooks:
        raise FileNotFoundError(
            f"В папке {input_dir} не найдено XLSX-файлов. "
            "Положите исходную таблицу в input/ и повторите запуск."
        )
    if len(workbooks) == 1:
        return workbooks[0]

    print("Найдено несколько Excel-файлов:")
    for index, path in enumerate(workbooks, start=1):
        print(f"  {index}. {path.name}")
    while True:
        answer = input("Выберите номер файла: ").strip()
        try:
            selected = int(answer)
        except ValueError:
            selected = 0
        if 1 <= selected <= len(workbooks):
            return workbooks[selected - 1]
        print(f"Введите число от 1 до {len(workbooks)}.")


def validate_imported_days(days: list[dict[str, Any]], days_dir: Path) -> list[str]:
    """Validate imported records against the same rules as committed day files."""
    errors: list[str] = []
    prepared: list[dict[str, Any]] = []
    for day in days:
        prepared_day = {**day, "_path": days_dir / f"{day.get('id', 'unknown')}.json"}
        prepared.append(prepared_day)
        errors.extend(validate_day(prepared_day))
    errors.extend(validate_day_collection(prepared))
    return errors


def archive_destination(source: Path, archive_dir: Path) -> Path:
    """Choose a non-overwriting archive filename."""
    candidate = archive_dir / source.name
    if not candidate.exists():
        return candidate
    counter = 2
    while True:
        candidate = archive_dir / f"{source.stem}-{counter}{source.suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def snapshot_files(paths: tuple[Path, ...]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def restore_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            path.unlink(missing_ok=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)


def initialize_client(name: str, short_name: str | None) -> int:
    args = ["--name", name]
    if short_name:
        args.extend(["--short-name", short_name])
    return init_client.main(args)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Инициализировать клиента и импортировать его меню из XLSX."
    )
    parser.add_argument("--input", type=Path, help="Путь к XLSX (по умолчанию поиск в input/)")
    parser.add_argument("--client", help="Имя клиента в первой строке листов Excel")
    parser.add_argument("--short-name", help="Короткое название приложения (необязательно)")
    parser.add_argument("--yes", action="store_true", help="Не запрашивать подтверждение")
    args = parser.parse_args(argv)

    try:
        workbook = choose_workbook(INPUT_DIR, args.input)
        client_name = (args.client or input("Введите имя клиента (как в заголовке Excel): ")).strip()
        if not client_name:
            raise ValueError("Имя клиента не должно быть пустым")
        short_name = args.short_name
        if short_name is not None:
            short_name = short_name.strip()
            if not short_name:
                raise ValueError("Короткое имя не должно быть пустым")

        if (ROOT / "client.json").exists() or (ROOT / "client-assets").exists():
            raise FileExistsError(
                "Найдены client.json или client-assets/. Для нового клиента используйте чистую копию шаблона."
            )
        if CLIENT_TEMPLATE_VERSION_PATH.exists():
            raise FileExistsError(
                "Похоже, этот репозиторий уже инициализирован: найден CLIENT_TEMPLATE_VERSION. "
                "Для нового клиента используйте чистую копию шаблона."
            )
        existing_json = sorted(DAYS_DIR.glob("*.json")) if DAYS_DIR.exists() else []
        if existing_json:
            raise FileExistsError(
                "В content/days/ уже есть JSON-файлы. Автоматическая инициализация "
                "разрешена только в чистом шаблоне: " + ", ".join(p.name for p in existing_json[:5])
            )

        print(f"\nИсходный файл: {workbook}")
        print(f"Клиент: {client_name}")
        print("Читаю листы Excel и извлекаю меню...")
        days = import_xlsx.extract_client_menus(workbook, client_name)
        if not days:
            raise ValueError(
                f"Не найдено ни одного дня для клиента {client_name!r}. "
                "Проверьте точное имя в первой строке листов."
            )

        validation_errors = validate_imported_days(days, DAYS_DIR)
        if validation_errors:
            details = "\n".join(f"  - {error}" for error in validation_errors)
            raise ValueError("Импортированные дни не прошли проверку:\n" + details)

        meals_count = sum(len(day["meals"]) for day in days)
        ingredients_count = sum(
            len(meal["ingredients"]) for day in days for meal in day["meals"]
        )
        print("\nБудет выполнено:")
        print(f"  Клиент: {client_name}")
        print(f"  XLSX: {workbook.name}")
        print(f"  Дней: {len(days)}")
        print(f"  Приёмов пищи: {meals_count}")
        print(f"  Ингредиентов: {ingredients_count}")
        print(f"  Каталог результата: {DAYS_DIR.relative_to(ROOT)}/")
        print(f"  Архив исходника: {ARCHIVE_DIR.relative_to(ROOT)}/")

        if not args.yes and input("\nПродолжить? [y/N]: ").strip().casefold() not in {"y", "yes", "д", "да"}:
            print("Отменено. Файлы не изменены.")
            return 0

        snapshot = snapshot_files(CONFIG_FILES)
        created_days: list[Path] = []
        try:
            init_result = initialize_client(client_name, short_name)
            if init_result:
                raise RuntimeError(f"Инициализация клиента завершилась с кодом {init_result}")

            import_xlsx.write_json_files(days, DAYS_DIR)
            created_days = [DAYS_DIR / f"{day['id']}.json" for day in days]

            # Построение индекса тем же кодом, который используется в CI.
            index_text = dump_json(build_index(days))
            write_text_atomic(INDEX_FILE, index_text)
        except Exception:
            for path in created_days:
                path.unlink(missing_ok=True)
            restore_files(snapshot)
            shutil.rmtree(ROOT / "client-assets", ignore_errors=True)
            raise

        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        destination = archive_destination(workbook, ARCHIVE_DIR)
        try:
            shutil.move(str(workbook), str(destination))
        except OSError as exc:
            print(
                f"\nМеню создано, но исходный XLSX не удалось переместить в архив: {exc}\n"
                f"Файл остался на месте: {workbook}",
                file=sys.stderr,
            )
            return 1

        print("\nКлиент успешно создан!")
        print(f"  Клиент: {client_name}")
        print(f"  Создано дней: {len(days)}")
        print(f"  Приёмов пищи: {meals_count}")
        print(f"  Ингредиентов: {ingredients_count}")
        print(f"  Индекс: {INDEX_FILE.relative_to(ROOT)}")
        try:
            archived_label = destination.relative_to(ROOT)
        except ValueError:
            archived_label = destination
        print(f"  Исходный XLSX перемещён: {archived_label}")
        print("\nДалее проверьте сайт локально, затем выполните git status и закоммитьте изменения клиента.")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, zipfile.BadZipFile, ET.ParseError) as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
