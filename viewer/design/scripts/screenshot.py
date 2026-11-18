"""Capture a browser screenshot with Selenium + the system Firefox.

The in-app browser screenshot tool needs a visible desktop window; this script
works headlessly and is the standard verification path for the viewer.

    uv run --with selenium python viewer/design/scripts/screenshot.py \
        --url http://127.0.0.1:3000/ --output /tmp/opencode/viewer.png

Optional:
    --wait-text "KG Audit"      wait until the body contains this text
    --click-testid settings     click [data-testid="settings"] first
    --click-text "Audit"        click a visible button/link containing this text
    --width 1600 --height 1000
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

FIREFOX = os.environ.get(
    "FIREFOX_BINARY", "/snap/firefox/current/usr/lib/firefox/firefox"
)


def click_text(driver: webdriver.Firefox, text: str) -> None:
    driver.find_element(
        By.XPATH,
        f"//*[self::button or self::a or @role='button'][contains(normalize-space(.), '{text}')]",
    ).click()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3000/")
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--wait-text", default=None)
    parser.add_argument("--click-testid", default=None)
    parser.add_argument("--click-text", default=None)
    parser.add_argument("--settle", type=float, default=1.0)
    args = parser.parse_args()

    options = Options()
    options.add_argument("-headless")
    options.binary_location = FIREFOX
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(args.width, args.height)
    try:
        driver.get(args.url)
        if args.wait_text:
            WebDriverWait(driver, 20).until(
                lambda current: args.wait_text in current.find_element(
                    By.TAG_NAME, "body"
                ).text
            )
        if args.click_testid:
            driver.find_element(
                By.CSS_SELECTOR, f'[data-testid="{args.click_testid}"]'
            ).click()
        if args.click_text:
            click_text(driver, args.click_text)
        if args.settle:
            time.sleep(args.settle)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        if not driver.save_screenshot(str(output)):
            print("screenshot failed", file=sys.stderr)
            return 1
        print(str(output))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
