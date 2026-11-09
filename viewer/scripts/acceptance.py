"""Functional browser acceptance for the viewer.

Run from the repository root while the dev server is running:

    uv run --with selenium python viewer/scripts/acceptance.py
"""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / ".tmp-acceptance"
DOWNLOADS = TMP / "downloads"
BASE = os.environ.get("VIEWER_URL", "http://127.0.0.1:3000")


def viewer_url(query: str) -> str:
    snapshot = os.environ.get("VIEWER_SNAPSHOT", "reference")
    extra = "" if snapshot == "opentargets" else f"&snapshot={snapshot}"
    return f"{BASE}/?{query}{extra}"
FIREFOX = os.environ.get(
    "FIREFOX_BINARY", "/snap/firefox/current/usr/lib/firefox/firefox"
)


def wait(driver: webdriver.Firefox, selector: str, timeout: float = 20.0):
    return WebDriverWait(driver, timeout).until(
        lambda current: current.find_element(By.CSS_SELECTOR, selector)
    )


def wait_gone(driver: webdriver.Firefox, selector: str, timeout: float = 20.0) -> bool:
    return WebDriverWait(driver, timeout).until(
        lambda current: not current.find_elements(By.CSS_SELECTOR, selector)
    )


def wait_text(driver: webdriver.Firefox, text: str, timeout: float = 20.0) -> bool:
    return WebDriverWait(driver, timeout).until(
        lambda current: text.lower() in current.find_element(By.TAG_NAME, "body").text.lower()
    )


def el(driver: webdriver.Firefox, testid: str):
    return driver.find_element(By.CSS_SELECTOR, f'[data-testid="{testid}"]')


def click(driver: webdriver.Firefox, testid: str) -> None:
    button = el(driver, testid)
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
    driver.execute_script("arguments[0].click();", button)


def text(driver: webdriver.Firefox) -> str:
    return driver.find_element(By.TAG_NAME, "body").text


def testids(driver: webdriver.Firefox, prefix: str) -> list[str]:
    return [
        element.get_attribute("data-testid") or ""
        for element in driver.find_elements(By.CSS_SELECTOR, f'[data-testid^="{prefix}"]')
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


def modified_snapshot(source: Path, target: Path) -> None:
    data = json.loads(source.read_text())
    steps = data["workflow"]["steps"]
    steps.append(
        {
            "id": ["core", "review.probe"],
            "inputs": [],
            "outputs": [],
            "instruction": {"kind": ["sql", "duckdb"], "payload": {}},
            "assembly_preference": "eager",
        }
    )
    target.write_text(json.dumps(data))


def main() -> None:
    TMP.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for child in DOWNLOADS.glob("*"):
        child.unlink()
    compare_file = TMP / "compare.snapshot.json"
    modified_snapshot(ROOT / "public/data/reference.snapshot.json", compare_file)

    options = Options()
    options.add_argument("-headless")
    options.binary_location = FIREFOX
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.dir", str(DOWNLOADS))
    options.set_preference(
        "browser.helperApps.neverAsk.saveToDisk",
        "text/markdown,application/json,application/octet-stream",
    )
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1920, 1200)
    results: dict[str, object] = {}

    try:
        driver.get(viewer_url("view=workflow"))
        wait(driver, '[data-testid="workflow-canvas"]')
        wait(driver, '[data-testid^="step-"]')
        driver.execute_script("localStorage.clear()")
        driver.get(viewer_url("view=workflow"))
        wait(driver, '[data-testid="workflow-canvas"]')
        time.sleep(0.5)
        results["workflowSteps"] = step_cards(driver)
        results["groupChips"] = len(testids(driver, "group-chip-"))

        click(driver, "group-toggle-core")
        time.sleep(0.4)
        results["collapsedSteps"] = step_cards(driver)
        click(driver, "expand-all")
        time.sleep(0.5)
        results["expandedSteps"] = step_cards(driver)

        click(driver, "group-mode-emitter")
        time.sleep(0.5)
        results["emitterGroups"] = len(testids(driver, "group-chip-"))
        click(driver, "group-mode-component")
        time.sleep(0.3)

        click(driver, "tab-blueprint")
        wait(driver, '[data-testid="blueprint-canvas"]')
        time.sleep(0.8)
        results["blueprintNodes"] = len(testids(driver, "bp-node-"))
        results["propertyActions"] = len(
            [t for t in testids(driver, "bp-property-") if not t.startswith("bp-property-row-")]
        )
        click(driver, "readable-view")
        time.sleep(0.6)
        viewport = driver.find_element(By.CSS_SELECTOR, ".react-flow__viewport")
        transform = driver.execute_script(
            "return getComputedStyle(arguments[0]).transform", viewport
        )
        results["readableMode"] = {
            "pressed": el(driver, "readable-view").get_attribute("aria-pressed"),
            "transform": transform,
        }
        click(driver, "fit-view")
        time.sleep(0.4)

        click(driver, "bp-property-defect-condition_rating")
        wait(driver, '[data-testid="proof-receipt"]')
        wait_text(driver, "Unrated")
        results["conditionRatingLineage"] = {
            "receipt": "coalesce" in text(driver) and "Unrated" in text(driver),
            "impact": bool(driver.find_elements(By.CSS_SELECTOR, '[data-testid="lineage-impact"]')),
            "questions": bool(driver.find_elements(By.CSS_SELECTOR, '[data-testid="lineage-questions"]')),
            "url": driver.current_url,
        }

        driver.get(viewer_url("view=lineage&kind=node&component=reading&property=value"))
        wait(driver, '[data-testid="branch-comparison"]')
        time.sleep(0.5)
        results["readingBranches"] = {
            "branches": len(testids(driver, "branch-")),
            "temperature": "temperature" in text(driver),
            "vibration": "vibration" in text(driver),
            "questions": len(testids(driver, "lineage-question-")),
        }

        # Coverage cell -> filtered lineage.
        driver.get(viewer_url("view=review"))
        wait(driver, '[data-testid="review-tab-content"]')
        click(driver, "coverage-cell-defect-condition_rating-surveys")
        wait(driver, '[data-testid="lineage-canvas"]')
        wait(driver, '[data-testid="lineage-source-filter"]')
        results["coverageFilter"] = el(driver, "lineage-source-filter").text
        click(driver, "clear-source-filter")

        # Review entity -> filtered review.
        driver.get(viewer_url("view=blueprint"))
        wait(driver, '[data-testid="blueprint-canvas"]')
        click(driver, "review-entity-defect")
        wait(driver, '[data-testid="subject-filter"]')
        results["entityReviewFilter"] = el(driver, "subject-filter").text

        # Rail navigation must scroll the panel body, never the document:
        # a document scroll shifts the whole workbench and leaves a blank page.
        driver.get(viewer_url("view=review"))
        wait(driver, '[data-testid="review-tab-content"]')
        rail_scroll = []
        for rail in (
            "summary",
            "findings",
            "questions",
            "coverage",
            "decisions",
            "build",
            "diff",
            "dossier",
        ):
            click(driver, f"review-rail-{rail}")
            time.sleep(0.15)
            rail_scroll.append(
                int(driver.execute_script("return Math.round(window.scrollY)"))
            )
        results["reviewRailScroll"] = rail_scroll
        results["reviewRailStable"] = all(value == 0 for value in rail_scroll)

        # Review queue: acknowledge + waive with a note.
        driver.get(viewer_url("view=review"))
        wait(driver, '[data-testid="review-tab-content"]')
        finding_ids = [
            t.removeprefix("finding-")
            for t in testids(driver, "finding-")
            if not t.startswith("finding-queue")
        ]
        unique = list(dict.fromkeys(finding_ids))
        first, second = unique[0], unique[1]
        click(driver, f"ack-{first}")
        time.sleep(0.4)
        click(driver, f"waive-{second}")
        note = el(driver, f"waive-note-{second}")
        note.send_keys("Accepted for the reference build review")
        click(driver, f"waive-save-{second}")
        time.sleep(0.5)
        results["queue"] = {
            "ack": "acknowledged" in text(driver).lower(),
            "waive": "waived" in text(driver).lower(),
            "stored": driver.execute_script(
                "return Object.keys(localStorage).some(k => k.includes('kg-viewer:review:'))"
            ),
        }

        # Pin baseline, then compare a modified snapshot.
        click(driver, "pin-baseline")
        time.sleep(0.4)
        compare_input = el(driver, "compare-input")
        compare_input.send_keys(str(compare_file))
        wait_text(driver, "added", 20)
        results["diff"] = el(driver, "diff-summary").text.replace("\n", " | ")[:400]

        # Dossier export.
        click(driver, "dossier-export-markdown")
        deadline = time.time() + 20
        exported: list[Path] = []
        while time.time() < deadline:
            completed = list(DOWNLOADS.glob("*.md"))
            partial = list(DOWNLOADS.glob("*.part"))
            if completed and not partial:
                exported = completed
                break
            time.sleep(0.3)
        payload = exported[0].read_text(errors="ignore") if exported else ""
        results["dossier"] = {
            "downloaded": [path.name for path in exported],
            "containsHeadings": bool(
                payload
                and "Audit findings" in payload
                and "Decision ledger" in payload
            ),
        }

        # Search.
        driver.get(viewer_url("view=workflow"))
        wait(driver, '[data-testid="workflow-canvas"]')
        search = el(driver, "search-input")
        search.send_keys("condition_rating")
        wait(driver, '[data-testid="search-results"]')
        wait(driver, '[data-testid="search-result-property"]')
        click(driver, "search-result-property")
        wait(driver, '[data-testid="lineage-canvas"]')
        results["search"] = "condition_rating" in text(driver)

        # Step detail and trace.
        driver.get(viewer_url("view=workflow"))
        wait(driver, '[data-testid="workflow-canvas"]')
        info_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-testid="step-info"]')
        driver.execute_script("arguments[0].click();", info_buttons[0])
        wait(driver, '[data-testid="step-detail"]')
        results["stepDetail"] = el(driver, "step-detail").text[:160]
        trace_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-testid="trace-step"]')
        if trace_buttons:
            driver.execute_script("arguments[0].click();", trace_buttons[0])
            wait(driver, '[data-testid="trace-banner"]')
            results["trace"] = el(driver, "trace-banner").text
            click(driver, "clear-focus")
            time.sleep(0.3)
            results["traceCleared"] = not bool(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid="trace-banner"]')
            )

        # Hover annotation popover.
        driver.get(viewer_url("view=blueprint"))
        wait(driver, '[data-testid="blueprint-canvas"]')
        pill = wait(driver, '[data-testid="annotation-pill"]')
        ActionChains(driver).move_to_element(pill).pause(0.5).perform()
        popover = wait(driver, '[data-testid="annotation-popover"]')
        opacity = driver.execute_script(
            "return getComputedStyle(arguments[0]).opacity", popover
        )
        results["annotationHover"] = {
            "opacity": opacity,
            "text": popover.text[:200],
        }

        # Keyboard navigation.
        driver.get(viewer_url("view=workflow"))
        wait(driver, '[data-testid="workflow-canvas"]')
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys("r")
        wait(driver, '[data-testid="review-tab-content"]')
        results["keyboardReview"] = True
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys("?")
        wait(driver, '[data-testid="shortcut-sheet"]')
        results["keyboardShortcuts"] = True
        body.send_keys(Keys.ESCAPE)
        time.sleep(0.3)
        results["shortcutClosed"] = not bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="shortcut-sheet"]')
        )

        results["localStorage"] = driver.execute_script(
            "return Object.keys(localStorage).filter(k => k.includes('kg-viewer:')).sort()"
        )
        results["finalUrl"] = driver.current_url
    finally:
        print(json.dumps(results, indent=2))
        driver.quit()


if __name__ == "__main__":
    main()
