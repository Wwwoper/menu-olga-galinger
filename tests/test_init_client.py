import json
from pathlib import Path

import init_client


def prepare_root(tmp_path: Path) -> Path:
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "meta.json").write_text('{"title":"Шаблон"}', encoding="utf-8")
    (tmp_path / "manifest.json").write_text('{"name":"Шаблон","short_name":"Меню"}', encoding="utf-8")
    (tmp_path / "index.html").write_text(
        '<title>Шаблон</title>\n'
        '<meta name="apple-mobile-web-app-title" content="Меню">\n'
        '<span id="mobile-current-day">Меню</span>\n'
        '<nav id="sidebar"><h1>Меню <button>☰</button></h1></nav>\n'
        '<div id="top-header"><h1>Шаблон</h1><p>Описание</p></div>',
        encoding="utf-8",
    )
    (tmp_path / "service-worker.js").write_text("const VERSION = 'v1';", encoding="utf-8")
    (tmp_path / "content" / "days").mkdir()
    return tmp_path


def test_init_client_escapes_html_and_updates_all_config(tmp_path, monkeypatch):
    root = prepare_root(tmp_path)
    monkeypatch.setattr(init_client, "ROOT", root)
    monkeypatch.setattr(init_client, "DAYS_DIR", root / "content" / "days")

    assert init_client.main(["--name", 'Меню <Клиента> & "VIP"', "--short-name", "A&B"]) == 0

    html = (root / "index.html").read_text(encoding="utf-8")
    assert "Меню &lt;Клиента&gt; &amp; &quot;VIP&quot;" in html
    assert "A&amp;B" in html
    assert "<Клиента>" not in html
    assert json.loads((root / "manifest.json").read_text(encoding="utf-8"))["name"] == 'Меню <Клиента> & "VIP"'
    assert json.loads((root / "content" / "meta.json").read_text(encoding="utf-8"))["title"] == 'Меню <Клиента> & "VIP"'


def test_init_client_fails_before_writing_when_marker_missing(tmp_path, monkeypatch):
    root = prepare_root(tmp_path)
    index_path = root / "index.html"
    index_path.write_text("<title>only</title>", encoding="utf-8")
    before_meta = (root / "content" / "meta.json").read_text(encoding="utf-8")
    before_manifest = (root / "manifest.json").read_text(encoding="utf-8")
    monkeypatch.setattr(init_client, "ROOT", root)
    monkeypatch.setattr(init_client, "DAYS_DIR", root / "content" / "days")

    assert init_client.main(["--name", "Новый клиент"]) == 1
    assert (root / "content" / "meta.json").read_text(encoding="utf-8") == before_meta
    assert (root / "manifest.json").read_text(encoding="utf-8") == before_manifest
