import json
from pathlib import Path

import init_client


def prepare_root(tmp_path: Path) -> Path:
    (tmp_path / "content" / "days").mkdir(parents=True)
    (tmp_path / "content" / "meta.json").write_text('{"title":"Шаблон"}', encoding="utf-8")
    (tmp_path / "manifest.json").write_text('{"name":"Шаблон"}', encoding="utf-8")
    (tmp_path / "index.html").write_text('<title>Шаблон</title>', encoding="utf-8")
    (tmp_path / "service-worker.js").write_text("const VERSION = 'v1';", encoding="utf-8")
    (tmp_path / "TEMPLATE_VERSION").write_text("1.2.3\n", encoding="utf-8")
    defaults = tmp_path / "shared" / "assets" / "default"
    defaults.mkdir(parents=True)
    for name in ("favicon.ico", "favicon-16x16.png", "favicon-32x32.png", "icon-192x192.png", "icon-512x512.png", "apple-touch-icon.png"):
        (defaults / name).write_bytes(b"asset")
    return tmp_path


def configure(root, monkeypatch):
    monkeypatch.setattr(init_client, "ROOT", root)
    monkeypatch.setattr(init_client, "DAYS_DIR", root / "content" / "days")
    monkeypatch.setattr(init_client, "TEMPLATE_VERSION_PATH", root / "TEMPLATE_VERSION")
    monkeypatch.setattr(init_client, "CLIENT_TEMPLATE_VERSION_PATH", root / "CLIENT_TEMPLATE_VERSION")


def test_init_client_creates_private_config_and_assets_without_touching_template(tmp_path, monkeypatch):
    root = prepare_root(tmp_path)
    configure(root, monkeypatch)
    before = {name: (root / name).read_bytes() for name in ("index.html", "content/meta.json", "manifest.json")}

    assert init_client.main(["--name", 'Меню <Клиента> & "VIP"', "--short-name", "A&B"]) == 0

    config = json.loads((root / "client.json").read_text(encoding="utf-8"))
    assert config["name"] == 'Меню <Клиента> & "VIP"'
    assert config["shortName"] == "A&B"
    assert all((root / path).is_file() for path in config["assets"].values())
    assert {name: (root / name).read_bytes() for name in before} == before
    assert (root / "CLIENT_TEMPLATE_VERSION").read_text(encoding="utf-8") == "1.2.3\n"


def test_init_client_refuses_existing_client_config(tmp_path, monkeypatch):
    root = prepare_root(tmp_path)
    configure(root, monkeypatch)
    (root / "client.json").write_text("{}", encoding="utf-8")
    assert init_client.main(["--name", "Клиент"]) == 1
    assert (root / "client.json").read_text(encoding="utf-8") == "{}"
