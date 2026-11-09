"use client";

import { FileText } from "lucide-react";

import { ACTIVITY_LABELS, DEFAULT_TABS, editorTabLabel } from "./defaults";
import { EditorTabs } from "./EditorTabs";
import { getFeature } from "./features";
import { useWorkbench } from "./store";

export function EditorArea() {
  const { state, actions } = useWorkbench();
  const activity = state.activity;
  const feature = getFeature(activity);
  const layout = state.functions[activity].layout;
  const activeTab = layout.activeTab;

  return (
    <section className="wb-editor" aria-label={`${ACTIVITY_LABELS[activity]} editor`}>
      <EditorTabs />
      <div
        className="wb-editor-body thin-scrollbar"
        data-full-bleed={activity === "topology" ? "true" : undefined}
        data-testid="editor-body"
      >
        {activeTab ? (
          <feature.Editor state={state} actions={actions} activity={activity} />
        ) : (
          <div className="wb-editor-empty">
            <FileText aria-hidden className="size-6" />
            <p className="wb-editor-empty-title">No editor is open</p>
            <p className="wb-editor-empty-copy">
              Open a {ACTIVITY_LABELS[activity].toLowerCase()} editor from the
              command palette or start with the default tab.
            </p>
            <div className="wb-editor-empty-actions">
              {DEFAULT_TABS[activity].openTabs.map((tab) => (
                <button
                  key={tab}
                  type="button"
                  className="wb-button"
                  onClick={() => actions.openTab(activity, tab)}
                >
                  <FileText aria-hidden className="size-3" />
                  {editorTabLabel(tab)}
                </button>
              ))}
              <button
                type="button"
                className="wb-button"
                onClick={() => actions.setActiveTab(activity, layout.openTabs[0] ?? null)}
                disabled={layout.openTabs.length === 0}
              >
                Restore active tab
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
