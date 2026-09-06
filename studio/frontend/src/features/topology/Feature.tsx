"use client";

/**
 * Topology — the graph editor.
 *
 * PROP CONTRACT (`FeatureProps`, see `src/lib/types.ts`):
 *   document      The current IR document. Node and edge components are
 *                 `document.components`; canvas positions are
 *                 `document.views.topology["component:<id>"]`; the slots a node shows
 *                 are `document.components[].properties` (plus inherited ones in
 *                 `index.components[].resolved_properties`). Never null in the shell.
 *   index         `AuthoringIndex`: `components[]` gives resolved properties and
 *                 `endpoint_is_category`, `selectable[]` is what a binding may read.
 *   problems      Problems whose ref resolves to this area (component:/binding:),
 *                 pre-filtered by the shell — rendered inline via per-ref badges.
 *   selectedRef   The globally selected IR ref.
 *   onSelectRef   Move the global selection; the inspector dock and every other area
 *                 follow it. Pass null to clear.
 *   apply         The only way to change the document.
 *
 * The canvas, the scope strip and the add/name flows are wired here; the document surgery
 * and the three-tier rules live in `logic.ts`; the right-hand inspector registers itself
 * through `inspector.ts`.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

import { Panel } from "@/components/ui";
import { useSelectionStore } from "@/stores/selectionStore";
import { componentsOf, createComponent, componentRef, freePosition, withPosition } from "./logic";
import { AddNodeModal } from "./AddNodeModal";
import { ScopeStrip } from "./ScopeStrip";
import { TopologyCanvas } from "./TopologyCanvas";
import { registerTopologyInspector } from "./inspector";
import type { FeatureProps } from "@/lib/types";
import { DEFAULT_FILTERS, type TopologyFilters } from "./logic";

export default function TopologyFeature({
  document,
  problems,
  selectedRef,
  onSelectRef,
  apply,
}: FeatureProps) {
  const [filters, setFilters] = useState<TopologyFilters>(DEFAULT_FILTERS);
  const [addOpen, setAddOpen] = useState(false);
  const [revealId, setRevealId] = useState<string | null>(null);
  const revealToken = useSelectionStore((state) => state.revealToken);

  // The component inspector: registered while this area is mounted, dropped on unmount.
  useEffect(() => registerTopologyInspector(), []);

  const components = useMemo(() => componentsOf(document), [document]);

  const handleCreateNode = useCallback(
    (spec: Parameters<typeof createComponent>[1]) => {
      const { component, createdCategory } = createComponent(document, spec);
      apply((draft) => {
        let next = draft;
        if (createdCategory) {
          next = { ...next, components: [...(next.components ?? []), createdCategory] };
          next = withPosition(next, componentRef(createdCategory.id), freePosition(next));
        }
        next = { ...next, components: [...(next.components ?? []), component] };
        return withPosition(next, componentRef(component.id), freePosition(next));
      });
      // Keep the new component selected and ask the canvas to scroll it into view.
      onSelectRef(componentRef(component.id));
      setRevealId(component.id);
    },
    [document, apply, onSelectRef],
  );

  const locate = useCallback(
    (ref: string, id: string) => {
      onSelectRef(ref);
      setRevealId(id);
    },
    [onSelectRef],
  );

  return (
    <Panel
      title="Topology"
      subtitle={`${document.components?.length ?? 0} components · ${problems.length} problem${problems.length === 1 ? "" : "s"}`}
      padded={false}
      className="min-h-0 flex-1"
      bodyClassName="flex min-h-0 flex-1"
    >
      <ScopeStrip
        components={components}
        filters={filters}
        onFiltersChange={setFilters}
        onAddNode={() => setAddOpen(true)}
        onLocate={locate}
      />

      <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
        <TopologyCanvas
          document={document}
          filters={filters}
          selectedRef={selectedRef}
          revealToken={revealToken}
          revealId={revealId}
          onRevealConsumed={() => setRevealId(null)}
          onSelectRef={onSelectRef}
          apply={apply}
          onAddNode={() => setAddOpen(true)}
        />
      </div>

      <AddNodeModal
        open={addOpen}
        document={document}
        onClose={() => setAddOpen(false)}
        onCreate={handleCreateNode}
      />
    </Panel>
  );
}
