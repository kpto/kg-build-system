"use client";

import { DetailEditor } from "@/detail/DetailFeature";
import { cx } from "@kbs/design";
import { TopologyEditor } from "@/topology/TopologyFeature";
import {
  WorkflowEditor,
  WorkflowStepEditor,
} from "@/workflow/WorkflowFeature";
import { EditorTabs } from "./EditorTabs";
import styles from "./editorArea.module.css";
import { useWorkbench } from "./store";
import { documentSignature, type WorkbenchState, type WorkbenchTab } from "./types";

function paneState(state: WorkbenchState, tab: WorkbenchTab): WorkbenchState {
  return tab.id === state.activeTabId ? state : { ...state, activeTabId: tab.id };
}

export function EditorArea({
  sidebarVisible,
  onToggleSidebar,
}: {
  sidebarVisible: boolean;
  onToggleSidebar(): void;
}) {
  const { state, actions } = useWorkbench();

  return (
    <section className={styles.editor} aria-label="Design editor">
      <EditorTabs
        sidebarVisible={sidebarVisible}
        onToggleSidebar={onToggleSidebar}
      />
      <div
        className={cx(styles.editorBody, "thin-scrollbar")}
        data-testid="editor-body"
      >
        {state.tabs.map((tab) => {
          const active = tab.id === state.activeTabId;
          const fullBleed =
            tab.document.kind === "graph" || tab.document.kind === "workflow";
          const step =
            tab.document.kind === "subject" &&
            tab.document.selection.kind === "step";
          const Editor =
            tab.document.kind === "graph"
              ? TopologyEditor
              : tab.document.kind === "workflow"
                ? WorkflowEditor
                : step
                  ? WorkflowStepEditor
                  : DetailEditor;
          const current = paneState(state, tab);
          return (
            <div
              key={`${tab.id}:${documentSignature(tab.document)}`}
              className={styles.editorPane}
              data-active={active ? "true" : undefined}
              data-full-bleed={fullBleed ? "true" : undefined}
              data-testid="editor-pane"
              data-tab-id={tab.id}
              aria-hidden={!active}
            >
              <Editor state={current} actions={actions} />
            </div>
          );
        })}
      </div>
    </section>
  );
}
