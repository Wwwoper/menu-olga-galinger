"""Сравнение новой страницы с legacy: нормализованный DOM всех секций и ссылок навигации.
Запуск из корня репозитория:  python tests/e2e/compare_legacy.py .
Нужны: pip install playwright && playwright install chromium
"""
import asyncio, subprocess, sys, time
from playwright.async_api import async_playwright

NORM = """
(root) => {
  const clone = root.cloneNode(true);
  clone.classList.remove('active'); clone.removeAttribute('style');
  if (!clone.getAttribute('class')) clone.removeAttribute('class');
  clone.querySelectorAll('template, .day-tools, .done-toggle').forEach(x => x.remove());
  clone.querySelectorAll('[data-grams]').forEach(x => x.removeAttribute('data-grams'));
  clone.querySelectorAll('[data-meal]').forEach(x => x.removeAttribute('data-meal'));
  const walk = (n) => {
    [...n.childNodes].forEach(c => {
      if (c.nodeType === 3 && !c.textContent.trim()) c.remove();
      else if (c.nodeType === 8) c.remove();
      else if (c.nodeType === 1) walk(c);
    });
  };
  walk(clone);
  return clone.outerHTML;
}
"""

async def collect(page, url):
    msgs = []
    page.on("console", lambda m: msgs.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: msgs.append(str(e)))
    await page.goto(url)
    await page.wait_for_selector(".day-section")
    n = await page.evaluate("document.querySelectorAll('.day-section').length")
    for i in range(n):
        await page.evaluate(f"document.querySelectorAll('.day-section')[{i}].scrollIntoView({{behavior:'instant'}})")
        await page.wait_for_timeout(60)
    await page.wait_for_timeout(500)
    out = {}
    for s in await page.query_selector_all(".day-section"):
        out[await s.get_attribute("id")] = await s.evaluate(NORM)
    nav = [await l.evaluate(NORM) for l in await page.query_selector_all(".nav-link")]
    return out, nav, msgs, await page.title()

async def main(root):
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            res = {}
            for name, url in (("legacy", "http://localhost:8765/legacy/index.legacy.html"), ("new", "http://localhost:8765/index.html")):
                ctx = await b.new_context(viewport={"width": 1280, "height": 900}, service_workers="block")
                res[name] = await collect(await ctx.new_page(), url)
                await ctx.close()
            await b.close()
    finally:
        srv.terminate()
    (ls, ln, lm, lt), (ns, nn, nm, nt) = res["legacy"], res["new"]
    print("sections", len(ls), len(ns), "nav", len(ln), len(nn))
    print("titles", lt, "|", nt)
    print("console errors legacy:", lm, "new:", nm)
    print("section diffs:", [k for k in ls if ls[k] != ns.get(k)])
    print("nav diffs:", [i for i, (a, b) in enumerate(zip(ln, nn)) if a != b], "(ожидаемо 43, 44: в legacy устарел data-search)")

asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "."))
