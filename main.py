import asyncio
import time
from datetime import datetime, timedelta
from pytz import timezone
import pyautogui
from playwright.async_api import async_playwright

# ================= НАСТРОЙКИ =================
URL = "https://www.camplife.com/1010/reservation/step1"  # <-- вставь сюда свой URL
TIMEZONE = "America/Los_Angeles"   # или другой, если у парка другой пояс
TARGET_TIME = "00:00:00"           # время клика (полночь)
HEADLESS = False                   # чтобы видеть окно браузера
BUTTON_TEXT = "Continue"           # текст кнопки, которую нужно нажать после первого клика
# =============================================

def get_target_dt():
    tz = timezone(TIMEZONE)
    now = datetime.now(tz)
    h, m, s = map(int, TARGET_TIME.split(":"))
    t = now.replace(hour=h, minute=m, second=s, microsecond=0)
    if t <= now:
        t += timedelta(days=1)
    return t

def wait_until(target):
    while True:
        now = datetime.now(target.tzinfo)
        diff = (target - now).total_seconds()
        if diff <= 0:
            break
        if diff > 0.5:
            time.sleep(min(0.25, diff - 0.5))

async def click_continue(page, text):
    """Ищет и нажимает кнопку Continue после первого клика"""
    print("[INFO] Ищу кнопку Continue...")
    try:
        # Пробуем по роли (если это button)
        await page.get_by_role("button", name=text).click(timeout=5000)
        print("✅ Кнопка 'Continue' нажата по роли.")
        return
    except:
        pass

    try:
        # Пробуем по тексту (если это div/a)
        await page.locator(f"text={text}").first.click(timeout=5000)
        print("✅ Кнопка 'Continue' нажата по тексту.")
        return
    except:
        print("❌ Не удалось найти кнопку 'Continue'. Возможно, другой текст или задержка.")
        try:
            # Выведем все видимые кнопки для отладки
            texts = await page.evaluate("""
                () => Array.from(document.querySelectorAll('button,[role="button"]'))
                          .map(b => (b.innerText || b.textContent || '').trim())
                          .filter(t => t.length)
            """)
            print("[DEBUG] Найденные кнопки:", texts)
        except:
            pass

async def main():
    target = get_target_dt()
    print(f"⏰ Ждём до {target.strftime('%Y-%m-%d %H:%M:%S %Z')}...")
    print("➡️ Наведи курсор на первую кнопку, которую нужно нажать в 00:00.")

    # Подготовим Playwright браузер заранее
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir="./camplife_profile",
            headless=False
        )
        page = await ctx.new_page()
        await page.goto(URL)
        print("[INFO] Войди и заполни все поля вручную. Скрипт всё сделает сам в полночь.")

        # Ждём точного времени
        wait_until(target)

        print("🖱️ Кликаю мышкой (в текущей позиции)...")
        pyautogui.click()

        # Даём странице 1–2 секунды обработать действие
        await asyncio.sleep(2)

        # После клика ищем кнопку Continue
        await click_continue(page, BUTTON_TEXT)

        print("⏳ Оставляю окно открытым на 10 минут для оплаты...")
        await asyncio.sleep(600)
        await ctx.close()

if __name__ == "__main__":
    asyncio.run(main())
