import json

from common import DAYS_DIR, INDEX_FILE, build_index, dump_json, load_day_files, validate_day, validate_day_collection


def test_all_days_valid_in_template_or_client():
    days = load_day_files()
    errors = [e for d in days for e in validate_day(d)]
    assert errors == []
    assert validate_day_collection(days) == []


def test_index_is_up_to_date():
    expected = dump_json(build_index(load_day_files()))
    assert INDEX_FILE.read_text(encoding="utf-8") == expected


def test_every_index_entry_has_file():
    index = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    for entry in index["days"]:
        assert (DAYS_DIR.parent / entry["file"]).exists()


def test_empty_template_index_is_valid():
    assert build_index([]) == {"mainDays": 0, "total": 0, "days": []}
