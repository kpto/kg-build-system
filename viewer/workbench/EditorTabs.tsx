"use client";

import {
  ArrowLeft,
  ArrowRight,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react";

import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { conceptForSelection } from "@/shared/ui/concepts";
import styles from "./editorTabs.module.css";
import { useWorkbench } from "./store";
import { documentTitle, type WorkbenchTab } from "./types";

function tabConcept(tab: WorkbenchTab) {
  const selection =
    tab.document.kind === "subject" ? tab.document.selection : undefined;
  return conceptForSelection(
    selection?.kind ?? tab.document.kind,
    selection?.level,
  );
}

export function EditorTabs({
  sidebarVisible,
  onToggleSidebar,
}: {
  sidebarVisible: boolean;
  onToggleSidebar(): void;
}) {
  const { state, actions } = useWorkbench();
  const canBack = state.historyIndex > 0;
  const canForward = state.historyIndex < state.history.length - 1;

  return (
    <div className={styles.tabbar} data-testid="editor-tabs">
      <div className={styles.tabnav} role="group" aria-label="Tab history">
        <button
          type="button"
          className={styles.tabnavButton}
          onClick={actions.back}
          disabled={!canBack}
          aria-label="Back"
          title="Back (Alt+Left)"
          data-testid="tab-back"
        >
          <ArrowLeft aria-hidden className="size-3.5" />
        </button>
        <button
          type="button"
          className={styles.tabnavButton}
          onClick={actions.forward}
          disabled={!canForward}
          aria-label="Forward"
          title="Forward (Alt+Right)"
          data-testid="tab-forward"
        >
          <ArrowRight aria-hidden className="size-3.5" />
        </button>
      </div>

      <div className={styles.tabs} role="tablist" aria-label="Open editors">
        {state.tabs.map((tab) => {
          const active = tab.id === state.activeTabId;
          const title = documentTitle(tab.document);
          const concept = tabConcept(tab);
          return (
            <div
              key={tab.id}
              className={styles.tab}
              data-active={active ? "true" : undefined}
              data-pinned={tab.pinned ? "true" : undefined}
              data-preview={tab.preview ? "true" : undefined}
              onMouseDown={(event) => {
                if (event.button === 1) event.preventDefault();
              }}
              onAuxClick={(event) => {
                if (event.button === 1) {
                  event.preventDefault();
                  actions.closeTab(tab.id);
                }
              }}
            >
              <button
                type="button"
                role="tab"
                aria-selected={active}
                className={styles.tabLabel}
                title={`${title} · ${tab.document.kind}${tab.preview ? " · preview" : ""}`}
                onClick={() => actions.activateTab(tab.id)}
                onDoubleClick={() => actions.pinTab(tab.id)}
                data-testid={`tab-${tab.id}`}
                data-concept={concept}
              >
                <ConceptGlyph concept={concept} className="size-3" />
                <span className={styles.tabTitle}>{title}</span>
              </button>
              {tab.pinned ? null : (
                <button
                  type="button"
                  className={styles.tabClose}
                  aria-label={`Close ${title}`}
                  title={`Close ${title}`}
                  onClick={() => actions.closeTab(tab.id)}
                >
                  <X aria-hidden className="size-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      <div className={styles.tabbarActions}>
        <button
          type="button"
          className={styles.tabnavButton}
          onClick={onToggleSidebar}
          aria-label={sidebarVisible ? "Hide side bar" : "Show side bar"}
          aria-pressed={sidebarVisible}
          title={sidebarVisible ? "Hide side bar (Ctrl/Cmd+B)" : "Show side bar (Ctrl/Cmd+B)"}
          data-testid="toggle-sidebar"
        >
          {sidebarVisible ? (
            <PanelLeftClose aria-hidden className="size-3.5" />
          ) : (
            <PanelLeftOpen aria-hidden className="size-3.5" />
          )}
        </button>
      </div>
    </div>
  );
}
