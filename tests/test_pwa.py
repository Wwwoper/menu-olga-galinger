import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def shell_list() -> list[str]:
    text = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    block = re.search(r"const SHELL = \[(.*?)\];", text, re.S).group(1)
    return re.findall(r"'([^']+)'", block)


def test_sw_precaches_shared_files_and_default_assets():
    shell = set(shell_list())
    expected = {p.relative_to(ROOT).as_posix() for p in (ROOT / "shared").rglob("*") if p.is_file()}
    expected |= {"index.html", "content/meta.json"}
    assert expected <= shell, f"нет в SHELL: {sorted(expected - shell)}"
    assert "client.json" in shell


def test_sw_shell_files_exist():
    for item in shell_list():
        if item not in {"./", "client.json", "manifest.json"}:
            assert (ROOT / item).is_file(), item


def test_sw_loads_and_caches_generated_index_and_client_days():
    text = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    assert "fetch('content/days.json'" in text
    assert "cache.put('content/days.json', response)" in text
    assert "cache.addAll(dayRequests)" in text
    assert "Object.values(client.assets || {})" in text


def test_manifest_builder_uses_client_identity_and_assets():
    from build_manifest import build_manifest

    config = {
        "name": "Клиент", "shortName": "К", "description": "Описание", "themeColor": "#123456",
        "assets": {"icon192": "client-assets/192.png", "icon512": "client-assets/512.png"},
    }
    manifest = build_manifest(config)
    assert manifest["name"] == "Клиент"
    assert manifest["short_name"] == "К"
    assert manifest["theme_color"] == "#123456"
    assert manifest["icons"][0]["src"] == "client-assets/192.png"
    assert manifest["start_url"] == "./" and manifest["scope"] == "./"


def test_index_links_pwa_files_and_client_config_hooks():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for needle in ('rel="manifest"', 'rel="apple-touch-icon"', 'name="theme-color"', 'id="client-favicon"'):
        assert needle in html
