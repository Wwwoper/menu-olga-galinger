import json

import create_client

GOOD_DAY = {
    "id": "day-1",
    "label": "1",
    "variantOf": None,
    "meals": [
        {
            "type": "breakfast",
            "dish": "Омлет",
            "ingredients": [{"name": "Яйцо", "grams": 100}],
        }
    ],
}


def configure_root(tmp_path, monkeypatch):
    root = tmp_path
    input_dir = root / "input"
    days_dir = root / "content" / "days"
    input_dir.mkdir()
    days_dir.mkdir(parents=True)
    (root / "content" / "meta.json").write_text('{"title":"Шаблон"}', encoding="utf-8")
    (root / "manifest.json").write_text('{"name":"Шаблон"}', encoding="utf-8")
    (root / "index.html").write_text("<title>Шаблон</title>", encoding="utf-8")
    (root / "TEMPLATE_VERSION").write_text("1.0.0\n", encoding="utf-8")

    monkeypatch.setattr(create_client, "ROOT", root)
    monkeypatch.setattr(create_client, "INPUT_DIR", input_dir)
    monkeypatch.setattr(create_client, "ARCHIVE_DIR", input_dir / "archive")
    monkeypatch.setattr(create_client, "DAYS_DIR", days_dir)
    monkeypatch.setattr(create_client, "INDEX_FILE", root / "content" / "days.json")
    monkeypatch.setattr(
        create_client,
        "CLIENT_TEMPLATE_VERSION_PATH",
        root / "CLIENT_TEMPLATE_VERSION",
    )
    monkeypatch.setattr(
        create_client,
        "CONFIG_FILES",
        (
            root / "content" / "meta.json",
            root / "manifest.json",
            root / "index.html",
            root / "CLIENT_TEMPLATE_VERSION",
            root / "content" / "days.json",
        ),
    )
    workbook = input_dir / "menus.xlsx"
    workbook.write_bytes(b"fake xlsx")
    return root, workbook


def test_create_client_imports_valid_days_and_archives_source(
    tmp_path, monkeypatch, capsys
):
    root, workbook = configure_root(tmp_path, monkeypatch)
    monkeypatch.setattr(
        create_client.import_xlsx, "extract_client_menus", lambda *_: [GOOD_DAY]
    )

    def fake_init(name, short_name):
        assert name == "Анна Иванова"
        assert short_name is None
        (root / "CLIENT_TEMPLATE_VERSION").write_text("1.0.0\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(create_client, "initialize_client", fake_init)

    assert create_client.main(["--client", "Анна Иванова", "--yes"]) == 0

    day_path = root / "content" / "days" / "day-1.json"
    assert json.loads(day_path.read_text(encoding="utf-8")) == GOOD_DAY
    index = json.loads((root / "content" / "days.json").read_text(encoding="utf-8"))
    assert index["total"] == 1
    assert not workbook.exists()
    assert (root / "input" / "archive" / "menus.xlsx").exists()
    assert "Клиент успешно создан" in capsys.readouterr().out


def test_create_client_rejects_invalid_import_before_initialization(
    tmp_path, monkeypatch
):
    root, workbook = configure_root(tmp_path, monkeypatch)
    invalid_day = {**GOOD_DAY, "id": "day-1-var-2", "variantOf": "day-1"}
    monkeypatch.setattr(
        create_client.import_xlsx, "extract_client_menus", lambda *_: [invalid_day]
    )
    called = False

    def fake_init(*_):
        nonlocal called
        called = True
        return 0

    monkeypatch.setattr(create_client, "initialize_client", fake_init)

    assert create_client.main(["--client", "Анна", "--yes"]) == 1
    assert not called
    assert workbook.exists()
    assert not (root / "CLIENT_TEMPLATE_VERSION").exists()
    assert not list((root / "content" / "days").glob("*.json"))


def test_create_client_refuses_non_empty_days_directory(tmp_path, monkeypatch):
    root, workbook = configure_root(tmp_path, monkeypatch)
    (root / "content" / "days" / "day-9.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        create_client.import_xlsx, "extract_client_menus", lambda *_: [GOOD_DAY]
    )

    assert create_client.main(["--client", "Анна", "--yes"]) == 1
    assert workbook.exists()


def test_archive_destination_does_not_overwrite(tmp_path):
    source = tmp_path / "menu.xlsx"
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "menu.xlsx").touch()
    (archive / "menu-2.xlsx").touch()

    assert create_client.archive_destination(source, archive) == archive / "menu-3.xlsx"


def test_menu_number_does_not_treat_date_suffix_as_day_number():
    from import_xlsx import Sheet, fallback_start_number, make_day_identity

    assert make_day_identity("меню 1.01.25", 7) == ("day-7", "7", None)
    assert fallback_start_number([Sheet("меню 1", "a"), Sheet("меню 44", "b")]) == 45
    assert make_day_identity("меню 33 (2вариант)", 8) == (
        "day-33-var-2",
        "33 (2)",
        "day-33",
    )


def test_import_writer_never_overwrites_existing_json(tmp_path):
    import pytest
    from import_xlsx import write_json_files

    output = tmp_path / "days"
    output.mkdir()
    existing = output / "day-1.json"
    existing.write_text("original", encoding="utf-8")

    with pytest.raises(FileExistsError):
        write_json_files([GOOD_DAY], output)

    assert existing.read_text(encoding="utf-8") == "original"
