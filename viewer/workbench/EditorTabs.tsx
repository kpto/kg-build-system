"use client";

import { X } from "lucide-react";

import { ACTIVITY_LABELS, editorTabLabel } from "./defaults";
import { useWorkbench } from "./store";

export function EditorTabs() {
  const { state, actions } = useWorkbench();
  const activity = state.activity;
  const layout = state.functions[activity].layout;
  const label = ACTIVITY_LABELS[activity];

  return (
    <div
      className="wb-tabbar"
      role="tablist"
      aria-label={`${label} editors`}
      data-testid="editor-tabs"
    >
      {layout.openTabs.length === 0 ? (
        <span className="wb-tabbar-empty">No open editors</span>
      ) : (
        layout.openTabs.map((tab) => {
          const active = layout.activeTab === tab;
          const text = editorTabLabel(tab);
          return (
            <div key={tab} className="wb-tab" data-active={active ? "true" : undefined}>
              <button
                type="button"
                role="tab"
                aria-selected={active}
                className="wb-tab-label"
                title={text}
                onClick={() => actions.setActiveTab(activity, tab)}
              >
                {text}
              </button>
              <button
                type="button"
                className="wb-tab-close"
                aria-label={`Close ${text}`}
                title={`Close ${text}`}
                onClick={() => actions.closeTab(activity, tab)}
              >
                <X aria-hidden className="size-3" />
              </button>
            </div>
          );
        })
      )}
    </div>
  );
}
