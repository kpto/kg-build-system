"""Headless acceptance pass for the design viewer.

    uv run --with selenium python scripts/verify_design.py \
        --url http://127.0.0.1:3000/ --output /tmp/opencode/design

Checks:
- no left activity toolbar and no workbench bottom panel
- Control and Detail are collapsible side-bar headers, both can be open
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
                    '[data-testid="sidebar-section-control"],'
                    ' [data-testid="sidebar-section-outline"]',
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

        def middle_click(element) -> None:
            driver.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('auxclick',"
                "{bubbles: true, cancelable: true, button: 1}))",
                element,
            )
            time.sleep(0.6)

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

        # The Workflow document is a pinned visualisation. Its step list lives
        # in Outline and a step opens its own detail document.
        workflow_tab = next(
            (
                el
                for el in driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                )
                if el.text.strip() == "Workflow"
            ),
            None,
        )
        report["checks"]["workflow_tab"] = workflow_tab is not None
        if workflow_tab:
            workflow_tab.click()
            time.sleep(1)
            report["checks"]["workflow_editor"] = bool(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid="workflow-editor"]')
            )
            report["checks"]["workflow_map"] = bool(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid="workflow-map"]')
            )
            report["checks"]["workflow_component_nodes"] = len(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="workflow-component-node"]'
                )
            )
            report["checks"]["workflow_controls"] = bool(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="workflow-controls"]'
                )
            )
            report["checks"]["workflow_outline_closed"] = (
                expanded().get("sidebar-section-outline") == "false"
            )

            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="sidebar-section-outline"]'
            ).click()
            time.sleep(0.8)
            report["checks"]["workflow_outline"] = bool(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="workflow-outline"]'
                )
            )
            report["checks"]["workflow_steps"] = len(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid="workflow-step"]')
            )
            report["checks"]["workflow_status"] = status()
            shot("02-workflow")

            query = driver.find_element(
                By.CSS_SELECTOR, '[data-testid="workflow-filter-query"]'
            )
            query.send_keys("binding")
            time.sleep(0.7)
            report["checks"]["workflow_filtered_steps"] = len(
                driver.find_elements(By.CSS_SELECTOR, '[data-testid="workflow-step"]')
            )
            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="workflow-reset"]'
            ).click()
            time.sleep(0.6)

            first_step = driver.find_elements(
                By.CSS_SELECTOR, '[data-testid="workflow-step"]'
            )[0]
            step_key = first_step.get_attribute("data-step-key")
            step_name = step_key.split("\u0000")[1]
            first_step.click()
            time.sleep(1)
            report["checks"]["workflow_step_tab"] = tabs()[-1]
            report["checks"]["workflow_step_title"] = tabs()[-1] == step_name
            report["checks"]["workflow_step_editor"] = bool(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="workflow-step-editor"]'
                )
            )
            report["checks"]["workflow_outline_after_step"] = bool(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="workflow-outline"]'
                )
            )
            report["checks"]["workflow_step_status"] = status()

            before_step_close = len(tabs())
            middle_click(
                driver.find_elements(
                    By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
                )[-1].find_element(By.XPATH, "..")
            )
            report["checks"]["workflow_step_tab_closes"] = (
                len(tabs()) == before_step_close - 1
            )

            workflow_wrapper = workflow_tab.find_element(By.XPATH, "..")
            middle_click(workflow_wrapper)
            report["checks"]["workflow_survives_middle_click"] = (
                "Workflow" in tabs()
            )

            driver.find_element(
                By.CSS_SELECTOR, '[data-testid="sidebar-section-outline"]'
            ).click()
            time.sleep(0.5)
            click_tab("Graph")

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
        report["checks"]["node_inspect_keeps_tabs"] = tabs() == ["Graph", "Workflow"]
        report["checks"]["node_status"] = status()
        shot("03-inspect")

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
        report["checks"]["property_inspect_keeps_tabs"] = tabs() == ["Graph", "Workflow"]
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
            tabs() == ["Graph", "Workflow", "target.approvedSymbol"]
            and preview_flags() == [False, False, False]
        )

        report["checks"]["control_follows_subject"] = (
            "no view controls" in driver.find_element(
                By.CSS_SELECTOR, '[data-testid="sidebar"]'
            ).text
        )

        # Opening Detail while Control is open leaves both open and adds an
        # adjustable separator between them.
        driver.find_element(
            By.CSS_SELECTOR, '[data-testid="sidebar-section-outline"]'
        ).click()
        time.sleep(0.7)
        report["checks"]["sidebar_after_open"] = expanded()
        report["checks"]["detail_groups"] = sorted(detail_groups())
        report["checks"]["no_data_groups"] = (
            "detail-group-relations" not in detail_groups()
            and "detail-group-projections" not in detail_groups()
        )
        report["checks"]["both_sections_open"] = (
            expanded().get("sidebar-section-control") == "true"
            and expanded().get("sidebar-section-outline") == "true"
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
        shot("04-detail-property")

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

        # Middle-click closes a subject tab but not a pinned document.
        before_middle = len(tabs())
        tree_rows()[1].click()
        time.sleep(0.9)
        subject_label = driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="editor-tabs"] .wb-tab-label'
        )[-1]
        middle_click(subject_label.find_element(By.XPATH, ".."))
        report["checks"]["middle_click_closes_subject"] = (
            len(tabs()) == before_middle
        )

        # A tab never changes the side bar and never brings back a bottom panel.
        report["checks"]["sidebar_unchanged_by_tabs"] = (
            expanded().get("sidebar-section-control") == "true"
            and expanded().get("sidebar-section-outline") == "true"
        )
        report["checks"]["no_bottom_panel_after_tabs"] = not driver.find_elements(
            By.CSS_SELECTOR, '[data-testid="bottom-panel"]'
        )

        # Per-tab scroll is preserved across activation.
        click_tab("Graph")
        report["checks"]["graph_has_inspector"] = bool(
            driver.find_elements(By.CSS_SELECTOR, '[data-testid="topology-inspector"]')
        )
        report["checks"]["control_follows_graph"] = (
            "KIND" in driver.find_element(
                By.CSS_SELECTOR, '[data-testid="sidebar"]'
            ).text
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

        # A tree row opens the subject it names, and node properties expand.
        first_node = tree_rows()[0]
        first_name = first_node.text.strip().split("\n")[0]
        node_row = first_node.find_element(By.XPATH, "..")
        node_row.find_element(
            By.CSS_SELECTOR, 'button[aria-label^="Expand"]'
        ).click()
        time.sleep(0.6)
        node_properties = first_node.find_element(
            By.XPATH, "../.."
        ).find_elements(By.CSS_SELECTOR, '[data-testid="detail-tree-property"]')
        report["checks"]["node_property_rows"] = len(node_properties)
        if node_properties:
            property_name = node_properties[0].text.strip()
            node_properties[0].click()
            time.sleep(0.9)
            report["checks"]["node_property_tab"] = tabs()[-1]
            report["checks"]["node_property_matches"] = (
                tabs()[-1] == f"{first_name}.{property_name}"
            )
        shot("05-graph")

        print(json.dumps(report, indent=2))
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
