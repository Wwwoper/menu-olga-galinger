import json
from pathlib import Path

import new_day


def test_new_day_creates_day_and_rebuilds_index(tmp_path, monkeypatch):
    days_dir = tmp_path / "content" / "days"
    days_dir.mkdir(parents=True)
    index_file = tmp_path / "content" / "days.json"
    source = {
        "id": "day-1", "label": "1", "variantOf": None,
        "meals": [{"type": "lunch", "dish": "Рыба", "ingredients": [{"name": "Рыба", "grams": 120}]}],
    }
    (days_dir / "day-1.json").write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(new_day, "DAYS_DIR", days_dir)
    monkeypatch.setattr(new_day, "INDEX_FILE", index_file)

    assert new_day.main(["day-2", "--label", "2", "--copy-from", "day-1"]) == 0
    created = json.loads((days_dir / "day-2.json").read_text(encoding="utf-8"))
    index = json.loads(index_file.read_text(encoding="utf-8"))
    assert created["meals"] == source["meals"]
    assert index["total"] == 2


def test_new_variant_requires_existing_main_day(tmp_path, monkeypatch):
    days_dir = tmp_path / "content" / "days"
    days_dir.mkdir(parents=True)
    monkeypatch.setattr(new_day, "DAYS_DIR", days_dir)
    monkeypatch.setattr(new_day, "INDEX_FILE", tmp_path / "content" / "days.json")

    assert new_day.main(["day-5-var-2", "--label", "5 (2)"]) == 1
    assert not (days_dir / "day-5-var-2.json").exists()


def test_new_day_rejects_invalid_copy_source_without_creating_target(tmp_path, monkeypatch):
    days_dir = tmp_path / "content" / "days"
    days_dir.mkdir(parents=True)
    bad_source = {"id": "day-1", "label": "1", "variantOf": None, "meals": ["не объект"]}
    (days_dir / "day-1.json").write_text(json.dumps(bad_source), encoding="utf-8")
    monkeypatch.setattr(new_day, "DAYS_DIR", days_dir)
    monkeypatch.setattr(new_day, "INDEX_FILE", tmp_path / "content" / "days.json")

    assert new_day.main(["day-2", "--label", "2", "--copy-from", "day-1"]) == 1
    assert not (days_dir / "day-2.json").exists()
