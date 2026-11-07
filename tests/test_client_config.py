import json
from pathlib import Path

import pytest

from client_config import load_client_config


def write_config(root: Path, **overrides):
    assets = {
        "favicon": "client-assets/favicon.ico",
        "favicon16": "client-assets/favicon-16x16.png",
        "favicon32": "client-assets/favicon-32x32.png",
        "icon192": "client-assets/icon-192x192.png",
        "icon512": "client-assets/icon-512x512.png",
        "appleTouchIcon": "client-assets/apple-touch-icon.png",
    }
    (root / "client-assets").mkdir()
    for value in assets.values():
        (root / value).write_bytes(b"icon")
    config = {"name": "Клиент", "shortName": "К", "description": "Описание", "themeColor": "#123456", "assets": assets}
    config.update(overrides)
    (root / "client.json").write_text(json.dumps(config), encoding="utf-8")


def test_load_client_config_validates_required_fields_and_assets(tmp_path):
    write_config(tmp_path)
    assert load_client_config(tmp_path)["name"] == "Клиент"


@pytest.mark.parametrize("field,value", [("name", ""), ("themeColor", "green")])
def test_load_client_config_rejects_invalid_values(tmp_path, field, value):
    write_config(tmp_path, **{field: value})
    with pytest.raises(ValueError):
        load_client_config(tmp_path)


def test_load_client_config_rejects_path_traversal(tmp_path):
    write_config(tmp_path)
    config = json.loads((tmp_path / "client.json").read_text())
    config["assets"]["icon192"] = "client-assets/../secret.png"
    (tmp_path / "client.json").write_text(json.dumps(config))
    with pytest.raises(ValueError, match="client-assets"):
        load_client_config(tmp_path)


def test_load_client_config_rejects_missing_asset(tmp_path):
    write_config(tmp_path)
    (tmp_path / "client-assets/icon-512x512.png").unlink()
    with pytest.raises(ValueError, match="не найден"):
        load_client_config(tmp_path)
