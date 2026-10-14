import pytest

from common import build_index, normalize_search, parse_id, search_string, sort_key


def day(id_, label=None, variant_of=None, dish=None, names=("Яйцо",)):
    return {
        "id": id_,
        "label": label or id_.split("-")[1],
        "variantOf": variant_of,
        "meals": [
            {
                "type": "lunch",
                "dish": dish,
                "ingredients": [{"name": n, "grams": 10} for n in names],
            }
        ],
    }


def test_parse_id():
    assert parse_id("day-33") == (33, 0)
    assert parse_id("day-33-var-2") == (33, 2)
    with pytest.raises(ValueError):
        parse_id("33")


def test_order_variant_after_main_and_numeric():
    ids = ["day-10", "day-2", "day-33-var-2", "day-33", "day-34"]
    assert sorted(ids, key=sort_key) == [
        "day-2",
        "day-10",
        "day-33",
        "day-33-var-2",
        "day-34",
    ]


def test_index_counts_and_independent_of_input_order():
    days = [day("day-2"), day("day-1"), day("day-1-var-2", "1 (2)", "day-1")]
    a = build_index(days)
    b = build_index(list(reversed(days)))
    assert a == b
    assert a["mainDays"] == 2 and a["total"] == 3
    assert [d["index"] for d in a["days"]] == [0, 1, 2]
    assert a["days"][1]["id"] == "day-1-var-2"
    meal = a["days"][0]["meals"][0]
    assert meal == {
        "t": "lunch",
        "d": None,
        "dn": None,
        "i": [{"s": "яйцо", "n": "Яйцо"}],
    }


def test_variant_of_must_exist():
    with pytest.raises(ValueError):
        build_index([day("day-1-var-2", "1 (2)", "day-9")])


def test_duplicate_ids():
    with pytest.raises(ValueError):
        build_index([day("day-1"), day("day-1")])


def test_normalize_search_rules():
    assert normalize_search("Творог 5% обычный") == "творог 5 обычный"
    assert normalize_search("Сыр 45–50%") == "сыр 45–50"
    assert normalize_search("Грибы + лук/баклажаны") == "грибы + лук баклажаны"
    assert normalize_search("СЁМГА / форель") == "семга форель"
    assert normalize_search("Пельмени «Бульмени»") == "пельмени бульмени"


def test_search_string_main_and_variant():
    assert (
        search_string(day("day-3", dish="Цезарь", names=("Яйцо отварное",)))
        == "3 день 3 цезарь яйцо отварное"
    )
    assert (
        search_string(day("day-33-var-2", "33 (2)", "day-33", names=("Каша",)))
        == "33 2 33 вариант 2 каша"
    )
