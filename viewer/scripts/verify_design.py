"""Headless acceptance pass for the design viewer.

    uv run --with selenium python scripts/verify_design.py \
        --url http://127.0.0.1:3000/ --output /tmp/opencode/design

Checks:
- no left activity toolbar
- Topology and Detail are collapsible side-bar headers
- clicking a node or property only inspects; it does not open a tab
- Open Detail opens a document and the Detail section follows the document
- one workbench geometry survives every document change
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

        def expanded() -> dict[str, str | None]:
            return {
                el.get_attribute("data-testid"): el.get_attribute("aria-expanded")
                for el in driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid^="sidebar-section-"]'
                )
            }

        report["checks"]["no_activity_toolbar"] = not driver.find_elements(
            By.CSS_SELECTOR, ".wb-activitybar"
        )
        report["checks"]["sections"] = sorted(expanded())
        report["checks"]["initial_expanded"] = expanded()
        report["checks"]["tabs_initial"] = tabs()
        report["checks"]["bottom_visible"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="bottom-panel"]')
        )
        topology_geometry = geometry()
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
        time.sleep(0.8)
        report["checks"]["node_inspect_keeps_tabs"] = tabs() == ["Graph"]
        report["checks"]["node_status"] = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Workbench status"]'
        ).text.replace("\n", " | ")
        shot("02-inspect")

        bottom = driver.find_element(By.CSS_SELECTOR, '[data-testid="bottom-panel"]')
        report["checks"]["topology_property_rows"] = len(
            bottom.find_elements(
                By.CSS_SELECTOR, "[data-testid='topology-properties'] button"
            )
        )
        bottom.find_elements(
            By.CSS_SELECTOR, "[data-testid='topology-properties'] button"
        )[0].click()
        time.sleep(0.8)
        report["checks"]["property_inspect_keeps_tabs"] = tabs() == ["Graph"]
        report["checks"]["property_status"] = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Workbench status"]'
        ).text.replace("\n", " | ")

        driver.find_element(
            By.CSS_SELECTOR, '[data-testid="topology-open-detail"]'
        ).click()
        time.sleep(1.2)
        report["checks"]["tabs_after_open"] = tabs()
        report["checks"]["sidebar_after_open"] = expanded()
        report["checks"]["sidebar_order"] = driver.execute_script(
            """
            const nodes = [...document.querySelectorAll(
              '[data-testid="sidebar-section-topology"], [data-testid="sidebar-section-detail"], .wb-side-section-body'
            )];
            return nodes.map((node) =>
              node.getAttribute("data-testid") || node.className.split(" ")[0]
            );
            """
        )
        report["checks"]["sidebar_independent_of_tab"] = (
            expanded().get("sidebar-section-topology") == "true"
            and expanded().get("sidebar-section-detail") == "false"
        )
        report["checks"]["bottom_after_open"] = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
        ).text.split("\n")[:2]
        report["checks"]["detail_editor"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="detail-editor"]')
        )
        report["checks"]["geometry_unchanged"] = geometry() == topology_geometry
        report["checks"]["detail_status"] = driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Workbench status"]'
        ).text.replace("\n", " | ")
        shot("03-detail-property")

        # Opening a section is a user action; a tab never changes it.
        driver.find_element(
            By.CSS_SELECTOR, '[data-testid="sidebar-section-detail"]'
        ).click()
        time.sleep(0.7)
        report["checks"]["detail_section_user_open"] = expanded().get(
            "sidebar-section-detail"
        )

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
            # Tab state: scroll position belongs to the tab pane.
            pane = driver.find_element(
                By.CSS_SELECTOR, '[data-testid="editor-pane"][data-active="true"]'
            )
            driver.execute_script("arguments[0].scrollTop = 240", pane)
            before_scroll = driver.execute_script(
                "return arguments[0].scrollTop", pane
            )
            graph_tab.click()
            time.sleep(0.7)
            property_tab = next(
                (
                    el
                    for el in driver.find_elements(
                        By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                    )
                    if el.text.strip() == "target.approvedSymbol"
                ),
                None,
            )
            if property_tab:
                property_tab.click()
                time.sleep(0.7)
                restored = driver.find_element(
                    By.CSS_SELECTOR,
                    '[data-testid="editor-pane"][data-active="true"]',
                )
                report["checks"]["tab_scroll_restored"] = (
                    driver.execute_script("return arguments[0].scrollTop", restored)
                    == before_scroll
                )
            # Mouse back/forward dispatch through the native mouse handlers.
            driver.execute_script(
                "window.dispatchEvent(new MouseEvent('mousedown',{button:3,bubbles:true}));"
                "window.dispatchEvent(new MouseEvent('mouseup',{button:3,bubbles:true}))"
            )
            time.sleep(0.6)
            report["checks"]["mouse_back_status"] = driver.find_element(
                By.CSS_SELECTOR, '[aria-label="Workbench status"]'
            ).text.replace("\n", " | ")
            driver.execute_script(
                "window.dispatchEvent(new MouseEvent('mousedown',{button:4,bubbles:true}));"
                "window.dispatchEvent(new MouseEvent('mouseup',{button:4,bubbles:true}))"
            )
            time.sleep(0.6)
            report["checks"]["mouse_forward_status"] = driver.find_element(
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
                time.sleep(0.7)
            report["checks"]["graph_tab_keeps_tabs"] = tabs() == [
                "Graph",
                "target.approvedSymbol",
            ]
            report["checks"]["sidebar_unchanged_by_graph_tab"] = expanded().get(
                "sidebar-section-detail"
            ) == "true"
            report["checks"]["bottom_unchanged_by_graph_tab"] = (
                driver.find_element(
                    By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
                ).text.split("\n")[:2]
                == report["checks"]["bottom_after_open"]
            )
            report["checks"]["graph_status"] = driver.find_element(
                By.CSS_SELECTOR, '[aria-label="Workbench status"]'
            ).text.replace("\n", " | ")
            shot("04-graph")
            report["checks"]["geometry_after_graph"] = geometry() == topology_geometry

        back = driver.find_element(By.CSS_SELECTOR, '[data-testid="tab-back"]')
        if back.get_attribute("disabled") is None:
            back.click()
            time.sleep(0.7)
            report["checks"]["back_status"] = driver.find_element(
                By.CSS_SELECTOR, '[aria-label="Workbench status"]'
            ).text.replace("\n", " | ")

        print(json.dumps(report, indent=2))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
