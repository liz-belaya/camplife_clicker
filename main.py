
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import cv2
import numpy as np
import pyautogui
from PIL import Image

# ============== SETTINGS ==============

TIMEZONE = "America/Los_Angeles"
TARGET_TIME = "00:00:00"

FOLDER = Path(__file__).parent

MAIN_BUTTON = FOLDER / "continue_button.png"
NOTICE_BUTTON = FOLDER / "continue_notice.png"

CONFIDENCE = 0.88
SEARCH_TIMEOUT = 12
MAX_RETRIES = 3

# ======================================

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


def next_target():
    zone = ZoneInfo(TIMEZONE)
    now = datetime.now(zone)

    h, m, s = map(int, TARGET_TIME.split(":"))

    target = now.replace(
        hour=h,
        minute=m,
        second=s,
        microsecond=0
    )

    if target <= now:
        target += timedelta(days=1)

    return target


def wait_until(target):
    zone = ZoneInfo(TIMEZONE)

    while True:
        remaining = (
            target - datetime.now(zone)
        ).total_seconds()

        if remaining <= 0:
            return

        time.sleep(min(0.05, remaining / 2))


def capture_screen():
    screenshot = pyautogui.screenshot()
    width, height = pyautogui.size()

    if screenshot.size != (width, height):
        screenshot = screenshot.resize(
            (width, height),
            Image.Resampling.BILINEAR
        )

    return cv2.cvtColor(
        np.array(screenshot.convert("RGB")),
        cv2.COLOR_RGB2GRAY
    )


def load_templates(path):
    image = cv2.imread(
        str(path),
        cv2.IMREAD_GRAYSCALE
    )

    if image is None:
        raise FileNotFoundError(
            f"Cannot load image: {path}"
        )

    templates = []

    for scale in (0.5, 0.625, 0.75, 1.0, 1.25):
        w = round(image.shape[1] * scale)
        h = round(image.shape[0] * scale)

        if w < 10 or h < 10:
            continue

        template = cv2.resize(
            image,
            (w, h),
            interpolation=cv2.INTER_AREA
        )

        templates.append(template)

    return templates


def find_button(templates, region=None):
    screen = capture_screen()
    height, width = screen.shape

    if region:
        left = int(width * region[0])
        top = int(height * region[1])
        right = int(width * region[2])
        bottom = int(height * region[3])

        area = screen[top:bottom, left:right]
    else:
        left = 0
        top = 0
        area = screen

    best_score = -1
    best_position = None

    for template in templates:
        h, w = template.shape

        if h > area.shape[0] or w > area.shape[1]:
            continue

        result = cv2.matchTemplate(
            area,
            template,
            cv2.TM_CCOEFF_NORMED
        )

        _, score, _, location = cv2.minMaxLoc(
            result
        )

        if score > best_score:
            best_score = score

            best_position = (
                left + location[0] + w // 2,
                top + location[1] + h // 2
            )

    if best_score >= CONFIDENCE:
        return best_position

    return None


def click_position(position):
    x, y = position

    print(f"[INFO] Clicking at x={x}, y={y}")

    pyautogui.click(x, y)


def search_main_button(templates, timeout=12):
    deadline = time.monotonic() + timeout
    attempts = 0

    while time.monotonic() < deadline:

        # Main Continue is usually bottom-right
        position = find_button(
            templates,
            region=(0.5, 0.45, 1.0, 1.0)
        )

        if position:
            return position

        attempts += 1

        # Scroll down if not visible
        if attempts % 3 == 0:
            width, height = pyautogui.size()

            pyautogui.moveTo(
                width // 2,
                height // 2
            )

            pyautogui.scroll(-6)

        time.sleep(0.1)

    return None


def search_notice_button(templates):
    # Site Notices modal appears near center
    return find_button(
        templates,
        region=(0.25, 0.2, 0.75, 0.85)
    )


def handle_continue(main_templates, notice_templates):

    print("[INFO] Searching for first Continue...")

    position = search_main_button(
        main_templates,
        SEARCH_TIMEOUT
    )

    if not position:
        print("[ERROR] First Continue not found.")
        return False

    click_position(position)
    print("[INFO] First Continue click sent.")

    # Check whether Site Notices opened,
    # otherwise retry main Continue.
    for attempt in range(MAX_RETRIES):

        time.sleep(1)

        notice = search_notice_button(
            notice_templates
        )

        if notice:
            print("[INFO] Site Notices detected.")
            click_position(notice)

            print(
                "[INFO] Site Notices Continue clicked."
            )
            return True

        print(
            f"[INFO] Site Notices not detected. "
            f"Checking main Continue "
            f"({attempt + 1}/{MAX_RETRIES})..."
        )

        # Retry only if still on the main page
        position = find_button(
            main_templates,
            region=(0.5, 0.45, 1.0, 1.0)
        )

        if position:
            click_position(position)
            print("[INFO] Main Continue clicked again.")
        else:
            print(
                "[INFO] Main Continue not visible. "
                "Checking for Site Notices..."
            )

    # One final check for a delayed modal
    time.sleep(1)

    notice = search_notice_button(
        notice_templates
    )

    if notice:
        click_position(notice)
        print("[INFO] Site Notices Continue clicked.")
        return True

    print(
        "[WARNING] Could not confirm Site Notices. "
        "Please check the page manually."
    )

    return False


def main():

    for image in (MAIN_BUTTON, NOTICE_BUTTON):
        if not image.exists():
            print(f"[ERROR] Missing image: {image}")
            return

    main_templates = load_templates(MAIN_BUTTON)
    notice_templates = load_templates(NOTICE_BUTTON)

    target = next_target()

    print("=" * 45)
    print("CAMPLIFE CLICKER — CHROME / SAFARI")
    print("=" * 45)

    print(
        "Target:",
        target.strftime("%Y-%m-%d %H:%M:%S %Z")
    )

    print()
    print("1. Open CampLife in Chrome or Safari.")
    print("2. Select campsite.")
    print("3. Fill in required information.")
    print("4. Open Check-out calendar.")
    print("5. Hover over Check-out date.")
    print("6. Do not move mouse.")
    print()

    print("[INFO] Waiting for target time...")

    wait_until(target)

    # FIRST CLICK — CHECK-OUT DATE
    pyautogui.click()

    print("[INFO] Check-out date click sent.")

    # CONTINUE BUTTONS
    handle_continue(
        main_templates,
        notice_templates
    )

    print()
    print("[INFO] Automation finished.")
    print("[INFO] Check reservation and payment.")

    input("Press Enter to finish...")


if __name__ == "__main__":
    main()
