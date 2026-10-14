from migrate_legacy import LegacyParser

SAMPLE = """
<a href="#day-1" class="nav-link" data-day="1" data-search="x">1</a>
<section id="day-1" class="day-section" data-index="0">
<h2 class="day-title">1</h2>
<div class="meals-grid" data-loaded="false"></div>
<template class="day-template"><div class="meal-card">
<h3>🌅 Завтрак</h3>
<div class="table-scroll"><table>
<thead><tr><th scope="col">Ингредиент</th><th scope="col">Граммовка</th></tr></thead>
<tbody><tr><td>Творог 5%</td><td class="grams">149 г</td></tr><tr><td>Пельмени «Бульмени»/самокат</td><td class="grams">175 г</td></tr></tbody>
<tbody class="extra-rows" hidden><tr><td>Грибы + лук (свежие)</td><td class="grams">5 г</td></tr></tbody>
</table></div>
</div><div class="meal-card">
<h3>🍽️ Обед <span class="dish-name">— Цезарь</span></h3>
<div class="table-scroll"><table><tbody><tr><td>Яйцо</td><td class="grams">52 г</td></tr></tbody></table></div>
</div></template>
</section>
<section id="day-1-var-2" class="day-section" data-index="1">
<h2 class="day-title">1 (2)</h2>
<template class="day-template"><div class="meal-card"><h3>🍓 Перекус</h3>
<table><tbody><tr><td>Банан</td><td class="grams">87 г</td></tr></tbody></table></div></template>
</section>
"""


def parse():
    p = LegacyParser()
    p.feed(SAMPLE)
    return p


def test_days_and_labels():
    p = parse()
    assert [d["id"] for d in p.days] == ["day-1", "day-1-var-2"]
    assert [d["label"] for d in p.days] == ["1", "1 (2)"]
    assert p.problems == []


def test_meals_dish_and_rows():
    d = parse().days[0]
    assert [m["type"] for m in d["meals"]] == ["breakfast", "lunch"]
    assert d["meals"][0]["dish"] is None
    assert d["meals"][1]["dish"] == "Цезарь"
    names = [i["name"] for i in d["meals"][0]["ingredients"]]
    assert names == ["Творог 5%", "Пельмени «Бульмени»/самокат", "Грибы + лук (свежие)"]
    assert d["meals"][0]["ingredients"][0]["grams"] == 149


def test_nav_captured():
    assert parse().nav["day-1"] == {"label": "1", "search": "x"}
