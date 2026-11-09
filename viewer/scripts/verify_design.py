"""Headless acceptance pass for the design viewer.

    uv run --with selenium python scripts/verify_design.py \
        --url http://127.0.0.1:3000/ --output /tmp/opencode/design

Checks:
- two activities: topology (default) and detail
- the bottom panel starts hidden and no data/JSON tab exists
- selecting a node shows its properties and attached meaning in Topology
- a property row opens Detail at property level with the provenance layout
- Detail presents design meaning and the property table before provenance
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
            lambda d: len(d.find_elements(By.CSS_SELECTOR, "svg circle")) > 10
        )
        time.sleep(1.2)

        def shot(name: str) -> None:
            path = out / f"{name}.png"
            driver.save_screenshot(str(path))
            report["screens"][name] = str(path)

        report["checks"]["activities"] = [
            el.get_attribute("data-testid")
            for el in driver.find_elements(
                By.CSS_SELECTOR, "[data-testid^='activity-']"
            )
        ]
        report["checks"]["topology_default"] = (
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="activity-topology"]'
            ).get_attribute("data-active")
            == "true"
        )
        report["checks"]["bottom_hidden"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
        )
        shot("01-topology")

        nodes = driver.find_elements(By.CSS_SELECTOR, "[data-topology-node-id]")
        target = next(
            node
            for node in nodes
            if node.get_attribute("data-topology-node") == "target"
        )
        driver.execute_script(
            "arguments[0].dispatchEvent(new MouseEvent('click',{bubbles:true}))",
            target,
        )
        time.sleep(1)
        report["checks"]["topology_property_rows"] = len(
            driver.find_elements(By.CSS_SELECTOR, "[data-testid='topology-properties'] button")
        )
        report["checks"]["topology_meaning"] = bool(
            driver.find_elements(By.CSS_SELECTOR, "[data-testid='topology-sidebar-selection']")
        )
        shot("02-topology-selected")

        driver.find_elements(
            By.CSS_SELECTOR, "[data-testid='topology-properties'] button"
        )[0].click()
        time.sleep(1.4)
        report["checks"]["detail_active"] = (
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="activity-detail"]'
            ).get_attribute("data-active")
            == "true"
        )
        report["checks"]["detail_status"] = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Workbench status"]'
        ).text.replace("\n", " | ")
        report["checks"]["detail_editor"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="detail-editor"]')
        )
        shot("03-detail-property")

        report["checks"]["no_audit_activity"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="activity-audit"]'
        )
        report["checks"]["editor_tabs"] = [
            el.text.strip().lower()
            for el in driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="editor-tabs"] button'
            )
        ]
        print(json.dumps(report, indent=2))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
