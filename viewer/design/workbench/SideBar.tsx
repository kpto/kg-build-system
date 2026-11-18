"use client";

import { useState } from "react";
import { ChevronRight } from "lucide-react";

import { ExplorerSidebar } from "@/detail/DetailFeature";
import { cx } from "@/shared/ui/theme";
import styles from "./sideBar.module.css";
import { useWorkbench } from "./store";

/**
 * The side bar is navigation only. A visualisation's controls live on the
 * visualisation itself, so this surface holds the Explorer and nothing else.
 */
export function SideBar() {
  const { state, actions } = useWorkbench();
  const [open, setOpen] = useState(true);
  const stats = state.index.stats;
  const explorerMeta = `${stats.topologyNodes} subjects · ${state.index.workflow.steps.length} steps`;

  return (
    <aside
      className={styles.sidebar}
      style={{ width: state.layout.sidebarWidth }}
      aria-label="Workbench side bar"
      data-testid="sidebar"
    >
      <section
        className={styles.sideSection}
        data-open={open ? "true" : undefined}
        data-testid="sidebar-section-body-explorer"
      >
        <button
          type="button"
          className={styles.sideSectionHeader}
          aria-expanded={open}
          onClick={() => setOpen((current) => !current)}
          data-testid="sidebar-section-explorer"
        >
          <ChevronRight
            aria-hidden
            className={cx("size-3 transition-transform", open && "rotate-90")}
          />
          <span className={styles.sideSectionTitle}>Explorer</span>
          <span className={styles.sideSectionMeta}>{explorerMeta}</span>
        </button>
        {open ? (
          <div className={cx(styles.sideSectionBody, "thin-scrollbar")}>
            <ExplorerSidebar state={state} actions={actions} />
          </div>
        ) : null}
      </section>
    </aside>
  );
}
