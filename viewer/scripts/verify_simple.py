"""Verify the pure-design viewer: three activities, low detail, no auditing.

    uv run --with selenium python scripts/verify_simple.py \
        --url http://127.0.0.1:3000/ --output /tmp/opencode/simple

Checks:
- default activity is Topology
- no audit/semantics activity or data/JSON bottom tab
- topology starts low detail (hub labels, no containment/semantics)
- Proof and Meaning render without a bottom panel
- bottom panel opens on demand and shows Selection/Details
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

FIREFOX = "/snap/firefox/current/usr/lib/firefox/firefox"
ACTIVITIES = ("topology", "proof", "meaning")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3000/")
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument("-headless")
    options.binary_location = FIREFOX
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(args.width, args.height)
    report: dict[str, object] = {"url": args.url, "screens": {}, "checks": {}}

    try:
        driver.get(args.url)
        driver.execute_script("window.localStorage.clear()")
        driver.refresh()
        WebDriverWait(driver, 40).until(
            lambda d: d.find_elements(By.CSS_SELECTOR, '[data-testid="workbench"]')
        )
        WebDriverWait(driver, 40).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "svg circle")) > 10
        )
        time.sleep(1.2)

        ids = [
            el.get_attribute("data-testid")
            for el in driver.find_elements(By.CSS_SELECTOR, "[data-testid^='activity-']")
        ]
        report["checks"]["activities"] = ids
        report["checks"]["topology_default"] = (
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="activity-topology"]'
            ).get_attribute("data-active")
            == "true"
        )
        report["checks"]["bottom_hidden"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
        )
        report["checks"]["node_labels"] = driver.execute_script(
            "return document.querySelectorAll('[data-testid=\"topology-canvas\"] g[data-topology-node-id] text').length"
        )
        report["checks"]["containment_links"] = driver.execute_script(
            "return document.querySelectorAll('[data-topology-link-kind=\"containment\"]').length"
        )
        report["screens"]["topology"] = str(out / "01-topology.png")
        driver.save_screenshot(report["screens"]["topology"])

        # Reveal all labels and containment through the Detail controls.
        for label in ("All", "Containment"):
            for button in driver.find_elements(By.TAG_NAME, "button"):
                if button.text.strip().lower() == label.lower():
                    button.click()
                    time.sleep(0.4)
                    break
        time.sleep(0.8)
        report["checks"]["labels_after_all"] = driver.execute_script(
            "return document.querySelectorAll('[data-testid=\"topology-canvas\"] g[data-topology-node-id] text').length"
        )
        report["checks"]["containment_after_toggle"] = driver.execute_script(
            "return document.querySelectorAll('[data-topology-link-kind=\"containment\"]').length"
        )
        report["screens"]["topology-detail"] = str(out / "02-topology-detail.png")
        driver.save_screenshot(report["screens"]["topology-detail"])

        for index, activity in enumerate(("proof", "meaning"), start=3):
            driver.find_element(
                By.CSS_SELECTOR, f'[data-testid="activity-{activity}"]'
            ).click()
            time.sleep(1.4)
            report["checks"][f"bottom_hidden_{activity}"] = not driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
            )
            report["checks"][f"{activity}_body"] = bool(
                driver.find_elements(By.CSS_SELECTOR, f'[data-testid="{activity}-editor"]')
            )
            report["screens"][activity] = str(out / f"0{index}-{activity}.png")
            driver.save_screenshot(report["screens"][activity])

        # Bottom panel on demand, then inspect its tabs.
        driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Show bottom panel"]'
        ).click()
        time.sleep(0.8)
        report["checks"]["bottom_open"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="bottom-panel"]')
        )
        tabs = [
            el.text.strip().lower()
            for el in driver.find_elements(By.CSS_SELECTOR, '[data-testid="bottom-panel"] button')
        ]
        report["checks"]["meaning_bottom_tabs"] = tabs
        report["checks"]["no_json_tab"] = not any(
            tab in {"data", "json"} for tab in tabs
        )
        report["screens"]["meaning-bottom"] = str(out / "05-meaning-bottom.png")
        driver.save_screenshot(report["screens"]["meaning-bottom"])

        print(json.dumps(report, indent=2))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
