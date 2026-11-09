"""Capture viewer screenshots with Selenium + the system Firefox.

Run from the repository root:

    uv run --with selenium python viewer/scripts/capture.py

The viewer dev server must already be running at http://127.0.0.1:3000.
Screenshots are written to viewer/screenshots/.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "screenshots"
BASE = os.environ.get("VIEWER_URL", "http://127.0.0.1:3000")


def viewer_url(query: str) -> str:
    snapshot = os.environ.get("VIEWER_SNAPSHOT", "reference")
    extra = "" if snapshot == "opentargets" else f"&snapshot={snapshot}"
    return f"{BASE}/?{query}{extra}"
FIREFOX = os.environ.get(
    "FIREFOX_BINARY", "/snap/firefox/current/usr/lib/firefox/firefox"
)


def wait_for(driver: webdriver.Firefox, selector: str, timeout: float = 20.0) -> None:
    WebDriverWait(driver, timeout).until(
        lambda current: current.find_elements(By.CSS_SELECTOR, selector)
    )


def wait_for_text(driver: webdriver.Firefox, text: str, timeout: float = 20.0) -> None:
    WebDriverWait(driver, timeout).until(
        lambda current: text in current.find_element(By.TAG_NAME, "body").text
    )


def shot(driver: webdriver.Firefox, name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    driver.save_screenshot(str(path))
    return path


def click(driver: webdriver.Firefox, testid: str) -> None:
    element = driver.find_element(By.CSS_SELECTOR, f'[data-testid="{testid}"]')
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
    driver.execute_script("arguments[0].click();", element)


def body_text(driver: webdriver.Firefox) -> str:
    return driver.find_element(By.TAG_NAME, "body").text


def testids(driver: webdriver.Firefox, prefix: str) -> list[str]:
    return [
        element.get_attribute("data-testid") or ""
        for element in driver.find_elements(
            By.CSS_SELECTOR, f'[data-testid^="{prefix}"]'
        )
    ]


def step_cards(driver: webdriver.Firefox) -> int:
    extras = {"step-info", "step-detail", "step-detail-close"}
    return len(
        [
            testid
            for testid in testids(driver, "step-")
            if testid not in extras and not testid.startswith("step-detail")
        ]
    )


def main() -> None:
    options = Options()
    options.add_argument("-headless")
    options.binary_location = FIREFOX
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1920, 1200)
    report: dict[str, object] = {}

    try:
        driver.get(viewer_url("view=workflow"))
        wait_for(driver, '[data-testid="workflow-canvas"]')
        wait_for(driver, ".react-flow__node")
        time.sleep(1.2)
        shot(driver, "01-workflow.png")

        report["workflow"] = {
            "nodes": len(driver.find_elements(By.CSS_SELECTOR, ".react-flow__node")),
            "edges": len(driver.find_elements(By.CSS_SELECTOR, ".react-flow__edge")),
            "groups": len(driver.find_elements(By.CSS_SELECTOR, '[data-testid^="group-chip-"]')),
            "stepCards": step_cards(driver),
        }

        click(driver, "group-toggle-core")
        time.sleep(0.8)
        shot(driver, "02-workflow-collapsed-core.png")
        report["collapsedCore"] = step_cards(driver)

        click(driver, "group-toggle-core")
        click(driver, "group-mode-emitter")
        time.sleep(0.8)
        shot(driver, "03-workflow-emitter.png")
        report["emitterGroups"] = [
            testid
            for testid in testids(driver, "group-chip-")
        ]

        click(driver, "group-mode-component")
        time.sleep(0.5)
        info_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-testid="step-info"]')
        if info_buttons:
            driver.execute_script("arguments[0].click();", info_buttons[0])
            wait_for(driver, '[data-testid="step-detail"]')
            time.sleep(0.4)
            shot(driver, "03b-step-detail.png")
            trace_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-testid="trace-step"]')
            if trace_buttons:
                driver.execute_script("arguments[0].click();", trace_buttons[0])
                wait_for(driver, '[data-testid="trace-banner"]')
                time.sleep(0.5)
                shot(driver, "03c-trace-mode.png")
                click(driver, "clear-focus")
                time.sleep(0.3)

        click(driver, "tab-blueprint")
        wait_for(driver, '[data-testid="blueprint-canvas"]')
        time.sleep(1.0)
        shot(driver, "04-blueprint.png")
        report["blueprint"] = {
            "nodes": len(driver.find_elements(By.CSS_SELECTOR, '[data-testid^="bp-node-"]')),
            "properties": len(
                [
                    testid
                    for testid in testids(driver, "bp-property-")
                    if not testid.startswith("bp-property-row-")
                ]
            ),
        }

        click(driver, "readable-view")
        time.sleep(0.8)
        shot(driver, "04b-blueprint-readable.png")

        # Hover annotation evidence while the readable cards are visible.
        pill = driver.find_element(By.CSS_SELECTOR, '[data-testid="annotation-pill"]')
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", pill)
        ActionChains(driver).move_to_element(pill).pause(0.8).perform()
        time.sleep(0.4)
        shot(driver, "04c-annotation-popover.png")
        report["annotation"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="annotation-popover"]')
        )

        click(driver, "fit-view")
        time.sleep(0.5)
        click(driver, "bp-property-defect-title")
        wait_for(driver, '[data-testid="lineage-canvas"]')
        wait_for(driver, '[data-testid="proof-receipt"]')
        time.sleep(1.0)
        shot(driver, "05-lineage-defect-title.png")
        report["lineage"] = {
            "nodes": len(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid^="lineage-node-"]')
            ),
            "receipt": "coalesce" in body_text(driver),
            "impact": len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="lineage-impact"]')),
        }

        click(driver, "tab-blueprint")
        wait_for(driver, '[data-testid="blueprint-canvas"]')
        click(driver, "bp-property-defect-condition_rating")
        wait_for(driver, '[data-testid="proof-receipt"]')
        wait_for_text(driver, "Unrated")
        time.sleep(1.0)
        shot(driver, "06-lineage-condition-rating.png")
        report["conditionRating"] = "Unrated" in body_text(driver)

        driver.get(viewer_url("view=lineage&kind=node&component=reading&property=value"))
        wait_for(driver, '[data-testid="branch-comparison"]')
        wait_for(driver, '[data-testid="lineage-questions"]')
        time.sleep(1.0)
        shot(driver, "07-lineage-reading-branches.png")
        report["readingBranches"] = {
            "branches": len(driver.find_elements(By.CSS_SELECTOR, '[data-testid^="branch-"]')),
            "temperature": "temperature" in body_text(driver),
            "vibration": "vibration" in body_text(driver),
            "questions": len(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid^="lineage-question-"]')
            ),
        }

        driver.get(viewer_url("view=review"))
        wait_for(driver, '[data-testid="review-tab-content"]')
        wait_for(driver, '[data-testid="findings-panel"]')
        time.sleep(1.2)
        shot(driver, "08-review.png")
        text = body_text(driver).lower()
        report["review"] = {
            "hasScore": "audit summary" in text or "score" in text,
            "hasQuestions": "design questions" in text,
            "hasCoverage": "coverage matrix" in text,
            "hasDecisions": "decision ledger" in text,
            "hasAIProvenance": "ai provenance" in text,
            "findings": len(
                [
                    testid
                    for testid in testids(driver, "finding-")
                    if not testid.startswith("findings-")
                ]
            ),
        }

        driver.execute_script(
            "document.querySelector('[data-testid=\"coverage-matrix\"]')?.scrollIntoView({block:'center'});"
        )
        time.sleep(0.5)
        shot(driver, "09-review-coverage.png")

        click(driver, "coverage-cell-defect-condition_rating-surveys")
        wait_for(driver, '[data-testid="lineage-source-filter"]')
        time.sleep(0.8)
        shot(driver, "09b-coverage-filtered-lineage.png")
        driver.get(viewer_url("view=review"))
        wait_for(driver, '[data-testid="review-tab-content"]')
        time.sleep(0.5)

        first_ack = driver.find_elements(By.CSS_SELECTOR, '[data-testid^="ack-"]')
        if first_ack:
            driver.execute_script("arguments[0].click();", first_ack[0])
            time.sleep(0.5)
            report["acknowledged"] = True

        click(driver, "pin-baseline")
        time.sleep(0.5)
        shot(driver, "10-review-baseline.png")
        report["baseline"] = "baseline" in body_text(driver).lower()

        driver.get(viewer_url("view=workflow"))
        wait_for(driver, '[data-testid="workflow-canvas"]')
        driver.find_element(By.TAG_NAME, "body").send_keys("?")
        time.sleep(0.5)
        shot(driver, "11-shortcuts.png")
        report["shortcuts"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="shortcut-sheet"]')
        )

        report["console"] = driver.execute_script(
            "return window.__viewerErrors || [];"
        )
    finally:
        print(json.dumps(report, indent=2))
        driver.quit()


if __name__ == "__main__":
    main()
