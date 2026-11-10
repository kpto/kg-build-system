"use client";

import { DetailEditor } from "@/detail/DetailFeature";
import { TopologyEditor } from "@/topology/TopologyFeature";
import {
  WorkflowEditor,
  WorkflowStepEditor,
} from "@/workflow/WorkflowFeature";
import { EditorTabs } from "./EditorTabs";
import { useWorkbench } from "./store";
import { documentSignature, type WorkbenchState, type WorkbenchTab } from "./types";

function paneState(state: WorkbenchState, tab: WorkbenchTab): WorkbenchState {
  return tab.id === state.activeTabId ? state : { ...state, activeTabId: tab.id };
}

export function EditorArea() {
  const { state, actions } = useWorkbench();

  return (
    <section className="wb-editor" aria-label="Design editor">
      <EditorTabs />
      <div className="wb-editor-body thin-scrollbar" data-testid="editor-body">
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
              className="wb-editor-pane"
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
