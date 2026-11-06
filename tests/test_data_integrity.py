from common import DAYS_DIR, build_index, load_day_files, validate_day, validate_day_collection


def test_all_days_valid_in_template_or_client():
    days = load_day_files()
    errors = [e for d in days for e in validate_day(d)]
    assert errors == []
    assert validate_day_collection(days) == []


def test_generated_index_matches_day_files():
    days = load_day_files()
    index = build_index(days)
    assert index["total"] == len(days)
    assert index["mainDays"] == sum(not day.get("variantOf") for day in days)
    assert len({entry["id"] for entry in index["days"]}) == len(days)


def test_every_index_entry_has_file():
    index = build_index(load_day_files())
    for entry in index["days"]:
        assert (DAYS_DIR.parent / entry["file"]).is_file()


def test_empty_template_index_is_valid():
    assert build_index([]) == {"mainDays": 0, "total": 0, "days": []}
