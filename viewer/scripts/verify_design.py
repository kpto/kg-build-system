"""Headless acceptance pass for the design viewer.

    uv run --with selenium python scripts/verify_design.py \
        --url http://127.0.0.1:3000/ --output /tmp/opencode/design

Checks:
- no left activity toolbar and no workbench bottom panel
- Topology and Detail are collapsible side-bar headers, both can be open
- the two open sections have an adjustable separator
- Detail tree groups start collapsed
- clicking a node or property only inspects; it does not open a tab
- the graph selection is a floating inspector inside the Graph document
- right-click "Go to Detail" opens a permanent document
- single-click opens/reuses one preview tab; double-click pins it
- one workbench geometry survives every document change
- per-tab editor state is preserved
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.action_chains import ActionChains
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
                const editor = document.querySelector('[data-testid="editor-body"]');
                return {
                  sidebar: Math.round(sidebar.getBoundingClientRect().width),
                  editor: Math.round(editor.getBoundingClientRect().height),
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

        def preview_flags() -> list[bool]:
            return [
                el.find_element(By.XPATH, "..").get_attribute("data-preview")
                == "true"
                for el in driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                )
            ]

        def expanded() -> dict[str, str | None]:
            return {
                el.get_attribute("data-testid"): el.get_attribute("aria-expanded")
                for el in driver.find_elements(
                    By.CSS_SELECTOR,
                    '[data-testid="sidebar-section-topology"],'
                    ' [data-testid="sidebar-section-detail"]',
                )
            }

        def detail_groups() -> dict[str, str | None]:
            return {
                el.get_attribute("data-testid"): el.get_attribute("aria-expanded")
                for el in driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid^="detail-group-"]'
                )
            }

        def status() -> str:
            return driver.find_element(
                By.CSS_SELECTOR, '[aria-label="Workbench status"]'
            ).text.replace("\n", " | ")

        def click_tab(title: str) -> bool:
            for el in driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
            ):
                if el.text.strip() == title:
                    el.click()
                    time.sleep(0.7)
                    return True
            return False

        def right_click(element) -> None:
            driver.execute_script(
                """
                const el = arguments[0];
                const rect = el.getBoundingClientRect();
                el.dispatchEvent(new MouseEvent('contextmenu', {
                  bubbles: true,
                  cancelable: true,
                  clientX: rect.left + 12,
                  clientY: rect.top + 12,
                }));
                """,
                element,
            )
            time.sleep(0.4)

        def choose_menu_item() -> None:
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="context-menu-item"]'
            ).click()
            time.sleep(0.9)

        report["checks"]["no_activity_toolbar"] = not driver.find_elements(
            By.CSS_SELECTOR, ".wb-activitybar"
        )
        report["checks"]["no_bottom_panel"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
        )
        report["checks"]["sections"] = sorted(expanded())
        report["checks"]["initial_expanded"] = expanded()
        report["checks"]["initial_detail_groups"] = detail_groups()
        report["checks"]["detail_groups_collapsed"] = all(
            value == "false" for value in detail_groups().values()
        )
        report["checks"]["tabs_initial"] = tabs()
        report["checks"]["inspector_initial"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="topology-inspector"]')
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
        report["checks"]["node_status"] = status()
        shot("02-inspect")

        inspector = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="topology-inspector"]'
        )
        report["checks"]["inspector_inside_graph"] = bool(
            driver.find_elements(
                By.CSS_SELECTOR,
                '[data-testid="editor-pane"][data-tab-id="graph"]'
                ' [data-testid="topology-inspector"]',
            )
        )
        property_buttons = inspector.find_elements(
            By.CSS_SELECTOR, "[data-testid='topology-properties'] button"
        )
        report["checks"]["topology_property_rows"] = len(property_buttons)
        property_buttons[0].click()
        time.sleep(0.8)
        report["checks"]["property_inspect_keeps_tabs"] = tabs() == ["Graph"]
        report["checks"]["property_status"] = status()

        # Close and reopen the floating inspector.
        driver.find_element(
            By.CSS_SELECTOR, '[aria-label="Close inspector"]'
        ).click()
        time.sleep(0.5)
        report["checks"]["inspector_closed"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="topology-inspector"]'
        )
        driver.find_element(
            By.CSS_SELECTOR, '[data-testid="topology-open-inspector"]'
        ).click()
        time.sleep(0.5)
        report["checks"]["inspector_reopened"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="topology-inspector"]')
        )

        # Right-click on a property row opens a context menu that creates a
        # permanent document tab.
        property_buttons = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="topology-inspector"]'
        ).find_elements(
            By.CSS_SELECTOR, "[data-testid='topology-properties'] button"
        )
        right_click(property_buttons[0])
        report["checks"]["context_menu_open"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="context-menu"]')
        )
        choose_menu_item()
        report["checks"]["tabs_after_context_menu"] = tabs()
        report["checks"]["context_menu_permanent"] = (
            tabs() == ["Graph", "target.approvedSymbol"]
            and preview_flags() == [False, False]
        )

        # Opening Detail while Topology is open leaves both open and adds an
        # adjustable separator between them.
        driver.find_element(
            By.CSS_SELECTOR, '[data-testid="sidebar-section-detail"]'
        ).click()
        time.sleep(0.7)
        report["checks"]["sidebar_after_open"] = expanded()
        report["checks"]["both_sections_open"] = (
            expanded().get("sidebar-section-topology") == "true"
            and expanded().get("sidebar-section-detail") == "true"
        )
        splitter = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="sidebar-splitter"]'
        )
        report["checks"]["sidebar_splitter"] = bool(splitter)
        if splitter:
            before_split = splitter[0].get_attribute("aria-valuenow")
            splitter[0].send_keys("\ue015")  # ArrowDown
            time.sleep(0.4)
            after_split = driver.find_element(
                By.CSS_SELECTOR, '[data-testid="sidebar-splitter"]'
            ).get_attribute("aria-valuenow")
            report["checks"]["sidebar_split_before"] = before_split
            report["checks"]["sidebar_split_after"] = after_split
            report["checks"]["sidebar_split_adjustable"] = before_split != after_split

        report["checks"]["detail_editor"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="detail-editor"]')
        )
        report["checks"]["geometry_unchanged"] = geometry() == topology_geometry
        report["checks"]["detail_status"] = status()
        shot("03-detail-property")

        # Detail tree groups start collapsed; expanding Nodes reveals rows.
        driver.find_element(By.CSS_SELECTOR, '[data-testid="detail-group-nodes"]').click()
        time.sleep(0.6)
        def tree_rows():
            return driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="detail-tree-node"]'
            )

        report["checks"]["detail_tree_rows"] = len(tree_rows())

        # Single-click opens one reusable preview tab.
        before_preview = tabs()
        tree_rows()[0].click()
        time.sleep(0.9)
        report["checks"]["preview_tabs"] = tabs()
        report["checks"]["preview_flags"] = preview_flags()
        report["checks"]["preview_opened"] = (
            len(tabs()) == len(before_preview) + 1 and preview_flags()[-1]
        )

        # The next single-click replaces the preview instead of adding a tab.
        preview_count = len(tabs())
        tree_rows()[1].click()
        time.sleep(0.9)
        report["checks"]["preview_reused"] = (
            len(tabs()) == preview_count and preview_flags()[-1]
        )
        report["checks"]["preview_reused_tabs"] = tabs()

        # Double-clicking a row pins the document.
        pinned_row = tree_rows()[2]
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'})", pinned_row
        )
        time.sleep(0.3)
        ActionChains(driver).double_click(pinned_row).perform()
        time.sleep(0.9)
        report["checks"]["double_click_tabs"] = tabs()
        report["checks"]["double_click_pinned"] = not preview_flags()[-1]

        # A later single-click creates a fresh preview tab.
        pinned_count = len(tabs())
        tree_rows()[0].click()
        time.sleep(0.9)
        report["checks"]["fresh_preview"] = (
            len(tabs()) == pinned_count + 1 and preview_flags()[-1]
        )
        report["checks"]["fresh_preview_tabs"] = tabs()

        # Double-clicking a tab label pins the preview as well.
        preview_labels = [
            el
            for el, preview in zip(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                ),
                preview_flags(),
            )
            if preview
        ]
        if preview_labels:
            ActionChains(driver).double_click(preview_labels[-1]).perform()
            time.sleep(0.8)
        report["checks"]["tab_label_pin"] = not any(preview_flags())

        # A tab never changes the side bar and never brings back a bottom panel.
        report["checks"]["sidebar_unchanged_by_tabs"] = (
            expanded().get("sidebar-section-topology") == "true"
            and expanded().get("sidebar-section-detail") == "true"
        )
        report["checks"]["no_bottom_panel_after_tabs"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
        )

        # Per-tab scroll is preserved across activation.
        click_tab("Graph")
        report["checks"]["graph_has_inspector"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="topology-inspector"]')
        )
        click_tab("target.approvedSymbol")
        pane = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="editor-pane"][data-active="true"]'
        )
        driver.execute_script("arguments[0].scrollTop = 240", pane)
        before_scroll = driver.execute_script("return arguments[0].scrollTop", pane)
        click_tab("Graph")
        click_tab("target.approvedSymbol")
        restored = driver.find_element(
            By.CSS_SELECTOR, '[data-testid="editor-pane"][data-active="true"]'
        )
        report["checks"]["tab_scroll_restored"] = (
            driver.execute_script("return arguments[0].scrollTop", restored)
            == before_scroll
        )
        report["checks"]["geometry_after_tabs"] = geometry() == topology_geometry
        shot("04-graph")

        print(json.dumps(report, indent=2))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
