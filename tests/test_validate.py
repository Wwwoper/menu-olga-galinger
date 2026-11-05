import copy
from pathlib import Path

import pytest

from common import validate_day, validate_day_collection

GOOD = {
    "id": "day-1", "label": "1", "variantOf": None,
    "meals": [{"type": "breakfast", "dish": None,
               "ingredients": [{"name": "Яйцо", "grams": 52}]}],
}


def errs(**patch):
    day = copy.deepcopy(GOOD)
    day.update(patch)
    return validate_day(day)


def test_good():
    assert errs() == []


def test_bad_id():
    assert errs(id="day-01x")


def test_id_must_match_filename():
    assert errs(_path=Path("day-2.json"))


def test_unknown_meal_type():
    assert errs(meals=[{"type": "brunch", "dish": None, "ingredients": [{"name": "a", "grams": 1}]}])


def test_duplicate_meal_type():
    meal = {"type": "lunch", "dish": None, "ingredients": [{"name": "a", "grams": 1}]}
    assert errs(meals=[meal, meal])


def test_grams_must_be_positive_int():
    for bad in (0, -1, 1.5, "10 г", True):
        meal = {"type": "lunch", "dish": None, "ingredients": [{"name": "a", "grams": bad}]}
        assert errs(meals=[meal]), bad


def test_html_in_name_rejected():
    meal = {"type": "lunch", "dish": None, "ingredients": [{"name": "<b>x</b>", "grams": 1}]}
    assert errs(meals=[meal])


@pytest.mark.parametrize("bad_day", [None, [], "day", 42])
def test_non_object_day_returns_error_instead_of_raising(bad_day):
    assert validate_day(bad_day)


@pytest.mark.parametrize("bad_meal", [None, [], "завтрак", 10])
def test_non_object_meal_returns_error_instead_of_raising(bad_meal):
    assert validate_day({**GOOD, "meals": [bad_meal]})


@pytest.mark.parametrize("bad_ingredient", [None, [], "яйцо", 10])
def test_non_object_ingredient_returns_error_instead_of_raising(bad_ingredient):
    meal = {"type": "breakfast", "dish": None, "ingredients": [bad_ingredient]}
    assert validate_day({**GOOD, "meals": [meal]})


def test_variant_id_must_match_variant_of():
    assert validate_day({**GOOD, "id": "day-3-var-2", "variantOf": "day-2"})


def test_main_day_cannot_have_variant_of():
    assert validate_day({**GOOD, "variantOf": "day-1"})


def test_variant_must_point_to_existing_main_day():
    variant = {**GOOD, "id": "day-1-var-2", "label": "1 (2)", "variantOf": "day-1"}
    assert validate_day_collection([variant])


def test_variant_cannot_point_to_another_variant():
    main = copy.deepcopy(GOOD)
    variant = {**GOOD, "id": "day-1-var-2", "label": "1 (2)", "variantOf": "day-1"}
    nested = {**GOOD, "id": "day-1-var-3", "label": "1 (3)", "variantOf": "day-1-var-2"}
    assert validate_day_collection([main, variant, nested])


def test_empty_collection_is_valid_for_template():
    assert validate_day_collection([]) == []
