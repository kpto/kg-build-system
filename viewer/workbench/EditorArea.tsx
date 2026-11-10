"use client";

import { ACTIVITY_LABELS } from "./defaults";
import { EditorTabs } from "./EditorTabs";
import { getFeature } from "./features";
import { useWorkbench } from "./store";

export function EditorArea() {
  const { state, actions } = useWorkbench();
  const activity = state.activity;
  const feature = getFeature(activity);

  return (
    <section className="wb-editor" aria-label={`${ACTIVITY_LABELS[activity]} editor`}>
      <EditorTabs />
      <div
        className="wb-editor-body thin-scrollbar"
        data-full-bleed={activity === "topology" ? "true" : undefined}
        data-testid="editor-body"
      >
        <feature.Editor state={state} actions={actions} activity={activity} />
      </div>
    </section>
  );
}
