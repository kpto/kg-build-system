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

        def geometry() -> dict[str, int]:
            return driver.execute_script(
                """
                const sidebar = document.querySelector('[data-testid="sidebar"]');
                const bottom = document.querySelector('[data-testid="bottom-panel"]');
                return {
                  sidebar: Math.round(sidebar.getBoundingClientRect().width),
                  bottom: Math.round(bottom.getBoundingClientRect().height),
                };
                """
            )

        def tabs() -> list[str]:
            return [
                el.text.strip()
                for el in driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                )
            ]

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
        report["checks"]["bottom_visible"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="bottom-panel"]')
        )
        topology_geometry = geometry()
        report["checks"]["tabs_initial"] = tabs()
        report["checks"]["sidebar_label"] = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="sidebar"]'
        ).text.split("\n")[0]
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
        bottom = driver.find_element(By.CSS_SELECTOR, '[data-testid="bottom-panel"]')
        report["checks"]["node_click_keeps_tabs"] = tabs() == ["Graph"]
        report["checks"]["topology_property_rows"] = len(
            bottom.find_elements(By.CSS_SELECTOR, "[data-testid='topology-properties'] button")
        )
        report["checks"]["sidebar_repeats_properties"] = bool(
            driver.find_elements(
                By.CSS_SELECTOR,
                "[data-testid='sidebar'] [data-testid='topology-properties']",
            )
        )
        report["checks"]["bottom_label"] = bottom.text.split("\n")[0]
        shot("02-topology-selected")

        driver.find_elements(
            By.CSS_SELECTOR, "[data-testid='topology-properties'] button"
        )[0].click()
        time.sleep(1.0)
        report["checks"]["property_tab_mode_stays_topology"] = (
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="activity-topology"]'
            ).get_attribute("data-active")
            == "true"
        )
        report["checks"]["tabs_after_property"] = tabs()
        driver.find_element(
            By.CSS_SELECTOR, '[data-testid="topology-open-detail"]'
        ).click()
        time.sleep(1.2)
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
        report["checks"]["tabs_after_open"] = tabs()
        report["checks"]["same_tab_after_mode_change"] = (
            report["checks"]["tabs_after_property"] == report["checks"]["tabs_after_open"]
        )
        report["checks"]["geometry_unchanged"] = geometry() == topology_geometry
        report["checks"]["back_enabled"] = (
            driver.find_element(By.CSS_SELECTOR, '[data-testid="tab-back"]').get_attribute(
                "disabled"
            )
            is None
        )
        driver.find_element(By.CSS_SELECTOR, '[data-testid="tab-back"]').click()
        time.sleep(0.7)
        report["checks"]["back_status"] = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Workbench status"]'
        ).text.replace("\n", " | ")
        driver.find_element(By.CSS_SELECTOR, '[data-testid="tab-forward"]').click()
        time.sleep(0.7)
        report["checks"]["forward_status"] = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Workbench status"]'
        ).text.replace("\n", " | ")

        graph_tab = next(
            (
                el
                for el in driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                )
                if el.text.strip() == "Graph"
            ),
            None,
        )
        if graph_tab:
            graph_tab.click()
            time.sleep(0.8)
            report["checks"]["graph_tab_keeps_detail_mode"] = (
                driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="activity-detail"]'
                ).get_attribute("data-active")
                == "true"
            )
        report["checks"]["detail_bottom_visible"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="bottom-panel"]')
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
