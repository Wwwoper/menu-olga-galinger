import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def shell_list() -> list[str]:
    text = (ROOT / "service-worker.js").read_text(encoding="utf-8")
    block = re.search(r"const SHELL = \[(.*?)\];", text, re.S).group(1)
    return re.findall(r"'([^']+)'", block)


def test_sw_precaches_every_shared_file_and_icon():
    shell = set(shell_list())
    expected = {p.relative_to(ROOT).as_posix() for p in (ROOT / "shared").rglob("*") if p.is_file()}
    expected |= {p.relative_to(ROOT).as_posix() for p in (ROOT / "icons").glob("*.png")}
    expected |= {"index.html", "manifest.json", "content/meta.json", "content/days.json"}
    assert expected <= shell, f"нет в SHELL: {sorted(expected - shell)}"


def test_sw_shell_files_exist():
    for item in shell_list():
        if item != "./":
            assert (ROOT / item).exists(), item


def test_manifest_is_relative_and_icons_exist():
    m = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert m["start_url"] == "./" and m["scope"] == "./"
    sizes = {i["sizes"] for i in m["icons"]}
    assert {"192x192", "512x512"} <= sizes
    for icon in m["icons"]:
        assert (ROOT / icon["src"]).exists()


def test_index_links_pwa_files():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    for needle in ('rel="manifest"', 'rel="apple-touch-icon"', 'name="theme-color"'):
        assert needle in html
