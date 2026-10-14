import copy
from pathlib import Path

from common import validate_day

GOOD = {
    "id": "day-1", "label": "1", "variantOf": None,
    "meals": [{"type": "breakfast", "dish": None,
               "ingredients": [{"name": "Яйцо", "grams": 52}]}],
}


def errs(**patch):
    d = copy.deepcopy(GOOD)
    d.update(patch)
    return validate_day(d)


def test_good():
    assert errs() == []


def test_bad_id():
    assert errs(id="day-01x")


def test_id_must_match_filename():
    assert errs(_path=Path("day-2.json"))


def test_unknown_meal_type():
    assert errs(meals=[{"type": "brunch", "dish": None, "ingredients": [{"name": "a", "grams": 1}]}])


def test_duplicate_meal_type():
    m = {"type": "lunch", "dish": None, "ingredients": [{"name": "a", "grams": 1}]}
    assert errs(meals=[m, m])


def test_grams_must_be_positive_int():
    for bad in (0, -1, 1.5, "10 г", True):
        meal = {"type": "lunch", "dish": None, "ingredients": [{"name": "a", "grams": bad}]}
        assert errs(meals=[meal]), bad


def test_html_in_name_rejected():
    meal = {"type": "lunch", "dish": None, "ingredients": [{"name": "<b>x</b>", "grams": 1}]}
    assert errs(meals=[meal])
