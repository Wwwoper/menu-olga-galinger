import json

from common import DAYS_DIR, INDEX_FILE, build_index, dump_json, load_day_files, validate_day


def test_all_real_days_valid():
    days = load_day_files()
    assert days, "нет файлов дней"
    errors = [e for d in days for e in validate_day(d)]
    assert errors == []


def test_index_is_up_to_date():
    expected = dump_json(build_index(load_day_files()))
    assert INDEX_FILE.read_text(encoding="utf-8") == expected


def test_every_index_entry_has_file():
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    for entry in index["days"]:
        assert (DAYS_DIR.parent / entry["file"]).exists()
