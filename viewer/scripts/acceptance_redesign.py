"""Headless acceptance pass for the redesigned KG Audit workbench.

Run while the viewer dev/prod server is running:

    uv run --with selenium python viewer/scripts/acceptance_redesign.py \
        --url http://127.0.0.1:3129/ --output /tmp/opencode/acceptance

It captures one screenshot per activity, measures the sidebar width and bottom
panel height for Proof, switches activities, and checks that the Proof layout is
restored (stable panels per function). It also checks the D3 topology has nodes
and links.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

FIREFOX = "/snap/firefox/current/usr/lib/firefox/firefox"
ACTIVITIES = ("proof", "audit", "semantics", "topology")


def measure(driver: webdriver.Firefox) -> dict[str, float]:
    return driver.execute_script(
        """
        const rect = (selector) => {
          const node = document.querySelector(selector);
          return node ? node.getBoundingClientRect() : null;
        };
        const sidebar = rect('[data-testid="sidebar"]');
        const bottom = rect('[data-testid="bottom-panel"]');
        const editor = rect('[data-testid="editor-body"]');
        return {
          sidebar: sidebar ? Math.round(sidebar.width) : 0,
          bottom: bottom ? Math.round(bottom.height) : 0,
          editor: editor ? Math.round(editor.height) : 0,
        };
        """
    )


def activate(driver: webdriver.Firefox, activity: str) -> None:
    driver.find_element(By.CSS_SELECTOR, f'[data-testid="activity-{activity}"]').click()
    WebDriverWait(driver, 20).until(
        lambda current: current.find_element(
            By.CSS_SELECTOR, '[data-testid="editor-body"]'
        ).is_displayed()
    )
    time.sleep(0.6)
    # Drop focus and move the pointer off the activity rail so its tooltip is
    # not in the screenshot.
    driver.execute_script("document.activeElement?.blur()")
    from selenium.webdriver import ActionChains
    ActionChains(driver).move_to_element(
        driver.find_element(By.CSS_SELECTOR, '[data-testid="editor-body"]')
    ).perform()
    time.sleep(0.2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3129/")
    parser.add_argument("--output", required=True)
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=1000)
    args = parser.parse_args()

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument("-headless")
    options.binary_location = FIREFOX
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(args.width, args.height)
    report: dict[str, object] = {"url": args.url, "screens": {}, "measures": {}}
    try:
        driver.get(args.url)
        WebDriverWait(driver, 30).until(
            lambda current: current.find_elements(
                By.CSS_SELECTOR, '[data-testid="workbench"]'
            )
        )
        time.sleep(1.0)

        # Stable per-function layout: Proof gets a custom sidebar and bottom.
        activate(driver, "proof")
        splitter = driver.find_element(
            By.CSS_SELECTOR, '[role="separator"][aria-orientation="vertical"]'
        )
        driver.execute_script("arguments[0].focus()", splitter)
        splitter.send_keys(Keys.ARROW_RIGHT)
        time.sleep(0.3)
        proof_before = measure(driver)
        driver.save_screenshot(str(output / "01-proof.png"))
        report["screens"]["proof"] = str(output / "01-proof.png")
        report["measures"]["proof_before"] = proof_before

        for activity in ("audit", "semantics", "topology"):
            activate(driver, activity)
            report["measures"][activity] = measure(driver)
            driver.save_screenshot(str(output / f"02-{activity}.png"))
            report["screens"][activity] = str(output / f"02-{activity}.png")

        activate(driver, "proof")
        proof_after = measure(driver)
        report["measures"]["proof_after"] = proof_after
        report["stable"] = proof_before == proof_after

        activate(driver, "topology")
        WebDriverWait(driver, 20).until(
            lambda current: current.find_elements(By.CSS_SELECTOR, "svg circle")
        )
        report["topology"] = driver.execute_script(
            """
            return {
              nodes: document.querySelectorAll('svg circle').length,
              links: document.querySelectorAll('svg line, svg path').length,
            };
            """
        )
        driver.save_screenshot(str(output / "03-topology.png"))
        report["screens"]["topology-final"] = str(output / "03-topology.png")

        print(json.dumps(report, indent=2))
        return 0 if report.get("stable") else 1
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
