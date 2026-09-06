/**
 * The inspector registry.
 *
 * The shell owns the dock and the selection; features own what a ref *means*. A
 * feature registers a panel at mount and the dock renders the highest-priority
 * match, falling back to the shell's generic summary, so the topology editor's node
 * inspector and the contract table's field inspector can share one slot without
 * knowing about each other.
 */

import type { ReactNode } from "react";

import type { ProjectDocument } from "@/lib/ir";
import type { InspectorPanel, InspectorProps } from "@/lib/types";

const panels = new Map<string, InspectorPanel>();

/** Register a panel; returns the unregister function for the caller's effect. */
export function registerInspector(panel: InspectorPanel): () => void {
  panels.set(panel.id, panel);
  return () => {
    panels.delete(panel.id);
  };
}

export function inspectorPanels(): InspectorPanel[] {
  return [...panels.values()].sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0));
}

export function resolveInspector(
  ref: string,
  document: ProjectDocument,
): InspectorPanel | null {
  for (const panel of inspectorPanels()) {
    try {
      if (panel.matches(ref, document)) return panel;
    } catch (error) {
      // A broken panel must not take the dock down with it.
      console.warn(`[inspector] panel ${panel.id} threw while matching`, error);
    }
  }
  return null;
}

/** The dock's single render entry point; `null` means "show the empty state". */
export function renderInspector(
  ref: string,
  props: Omit<InspectorProps, "ref">,
): { panel: InspectorPanel; content: ReactNode } | null {
  const panel = resolveInspector(ref, props.document);
  if (!panel) return null;
  return { panel, content: panel.render({ ...props, ref }) };
}
