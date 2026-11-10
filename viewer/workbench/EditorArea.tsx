"use client";

import { DetailEditor } from "@/detail/DetailFeature";
import { TopologyEditor } from "@/topology/TopologyFeature";
import { EditorTabs } from "./EditorTabs";
import { useWorkbench } from "./store";
import { activeDocument } from "./types";

export function EditorArea() {
  const { state, actions } = useWorkbench();
  const document = activeDocument(state);
  const graph = document.kind === "graph";
  const Editor = graph ? TopologyEditor : DetailEditor;

  return (
    <section className="wb-editor" aria-label="Design editor">
      <EditorTabs />
      <div
        className="wb-editor-body thin-scrollbar"
        data-full-bleed={graph ? "true" : undefined}
        data-testid="editor-body"
      >
        <Editor state={state} actions={actions} />
      </div>
    </section>
  );
}
