"""Проверка личных функций и PWA в Chromium.  python tests/e2e/features.py ."""
import asyncio, subprocess, sys, time
from playwright.async_api import async_playwright

URL = "http://localhost:8767/"
fails = []

def check(name, cond, extra=""):
    print(("OK   " if cond else "FAIL ") + name, extra)
    if not cond:
        fails.append(name)

async def main(root):
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch()
            ctx = await b.new_context(viewport={"width": 390, "height": 844})
            page = await ctx.new_page()
            errs = []
            page.on("pageerror", lambda e: errs.append(str(e)))
            await page.goto(URL)
            await page.wait_for_selector(".meal-card")

            # --- закрепление дня
            await page.evaluate("document.getElementById('day-12').scrollIntoView({behavior:'instant'})")
            await page.wait_for_selector("#day-12 .meal-card")
            await page.click("#day-12 .pin-btn")
            check("баннер показывает день 12", "день 12" in await page.inner_text(".today-link"))
            check("кнопка нажата", await page.get_attribute("#day-12 .pin-btn", "aria-pressed") == "true")
            await page.click("#day-12 .pin-btn")
            check("повторный клик снимает закрепление", await page.get_attribute("#day-12 .pin-btn", "aria-pressed") == "false")
            await page.click("#day-12 .pin-btn")
            await page.evaluate("document.getElementById('day-30').scrollIntoView({behavior:'instant'})")
            await page.wait_for_selector("#day-30 .meal-card")
            await page.click("#day-30 .pin-btn")
            await page.click("#day-12 .pin-btn") if False else None

            # --- порции
            g_before = await page.inner_text("#day-30 td.grams")
            await page.select_option("#day-30 .portion-select", "2")
            g_after = await page.inner_text("#day-30 td.grams")
            check("порции ×2 удваивают граммы", int(g_after.split()[0]) == 2 * int(g_before.split()[0]), f"{g_before} -> {g_after}")
            await page.evaluate("document.getElementById('day-5').scrollIntoView({behavior:'instant'})")
            await page.wait_for_selector("#day-5 .meal-card")
            check("порции действуют на другие дни", await page.input_value("#day-5 .portion-select") == "2")

            # --- отметки
            await page.check("#day-5 .meal-card >> nth=0 >> .done-check")
            check("карточка помечена", await page.evaluate("document.querySelector('#day-5 .meal-card').classList.contains('done')"))

            # --- перезагрузка: сохранение состояния и автопереход к закреплённому дню
            await page.goto(URL)
            await page.wait_for_selector("#day-30 .meal-card")
            await page.wait_for_timeout(600)
            top = await page.evaluate("document.getElementById('day-30').getBoundingClientRect().top")
            check("после перезагрузки открыт закреплённый день", abs(top) < 120, f"top={top:.0f}")
            check("порции сохранились", (await page.inner_text("#day-30 td.grams")) == g_after)
            await page.evaluate("document.getElementById('day-5').scrollIntoView({behavior:'instant'})")
            await page.wait_for_selector("#day-5 .meal-card")
            check("отметка сохранилась", await page.is_checked("#day-5 .meal-card >> nth=0 >> .done-check"))
            check("вторая карточка не помечена", not await page.is_checked("#day-5 .meal-card >> nth=1 >> .done-check"))

            # --- статистика
            await page.click("#stats-open")
            txt = await page.inner_text("#stats-dialog")
            check("статистика: 2 закрепления", "Закреплений: 2" in txt, txt.replace("\n", " | ")[:160])
            await page.click("#stats-dialog >> text=Закрыть")

            # --- смена даты: закрепление и отметки сбрасываются
            await page.evaluate("""() => {
              const y = new Date(Date.now() - 86400000);
              const p = n => String(n).padStart(2, '0');
              const ds = `${y.getFullYear()}-${p(y.getMonth()+1)}-${p(y.getDate())}`;
              const pin = JSON.parse(localStorage.getItem('menu-pinned')); pin.date = ds;
              localStorage.setItem('menu-pinned', JSON.stringify(pin));
              const d = JSON.parse(localStorage.getItem('menu-done')); d.date = ds;
              localStorage.setItem('menu-done', JSON.stringify(d));
            }""")
            await page.goto(URL + "#day-5")
            await page.reload()
            await page.wait_for_selector("#day-5 .meal-card")
            check("вчерашнее закрепление сброшено", "Выберите день" in await page.inner_text("#today-banner"))
            check("вчерашние отметки сброшены", not await page.is_checked("#day-5 .meal-card >> nth=0 >> .done-check"))
            check("якорь #day-5 имеет приоритет", abs(await page.evaluate("document.getElementById('day-5').getBoundingClientRect().top")) < 120)

            # --- PWA
            await page.goto(URL)
            await page.wait_for_selector(".meal-card")
            await page.evaluate("navigator.serviceWorker.ready.then(() => 1)")
            await page.wait_for_timeout(2500)
            keys = await page.evaluate("caches.keys().then(async ks => { const c = await caches.open(ks[0]); return [ks[0], (await c.keys()).length]; })")
            check("service worker закэшировал оболочку и дни", keys[1] >= 15 + 45, str(keys))
            srv.terminate(); srv.wait(); time.sleep(0.5)
            await page.reload()
            await page.wait_for_selector("#day-1 .meal-card", timeout=15000)
            check("офлайн: страница открывается", True)
            await page.evaluate("document.getElementById('day-40').scrollIntoView({behavior:'instant'})")
            await page.wait_for_selector("#day-40 .meal-card", timeout=15000)
            check("офлайн: произвольный день загружается", True)
            check("нет ошибок JS", not errs, str(errs))
            await b.close()
    finally:
        srv.terminate()
    print("ИТОГ:", "всё прошло" if not fails else f"провалено: {fails}")
    sys.exit(1 if fails else 0)

asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "."))
