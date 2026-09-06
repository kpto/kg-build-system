"use client";

import { useEffect, useMemo } from "react";

import { ChevronIcon, EmptyState, IconButton, Panel } from "@/components/ui";
import type { FeatureProps, InspectorProps, ProjectDocument } from "@/lib/types";
import { refLabel } from "@/lib/ids";
import { useProblemsForRef } from "@/stores/problemStore";
import { EntityInspector } from "./EntityInspector";
import { registerInspector, resolveInspector } from "./inspectorRegistry";

export interface InspectorDockProps {
  document: ProjectDocument;
  selectedRef: string | null;
  open: boolean;
  onToggle(): void;
  onSelectRef(ref: string | null): void;
  apply: FeatureProps["apply"];
}

/**
 * The right-hand dock.
 *
 * The shell's own `EntityInspector` registers at priority 0, so a feature that
 * registers a panel matching the same refs wins without the dock knowing anything
 * about features.
 */
export function InspectorDock({
  document,
  selectedRef,
  open,
  onToggle,
  onSelectRef,
  apply,
}: InspectorDockProps) {
  // Registering the fallback here (rather than at module load) keeps the registry
  // empty during SSR and on unmount.
  useEffect(
    () =>
      registerInspector({
        id: "shell.entity",
        label: "Entity",
        priority: 0,
        matches: (ref) => refLabel(ref).length > 0,
        render: (props) => <EntityInspector {...props} />,
      }),
    [],
  );

  const problems = useProblemsForRef(selectedRef);
  const rendered = useMemo(() => {
    if (!selectedRef) return null;
    const props: InspectorProps = { document, ref: selectedRef, problems, onSelectRef, apply };
    const panel = resolveInspector(selectedRef, document);
    if (!panel) return null;
    return { panel, content: panel.render(props) };
  }, [document, selectedRef, problems, onSelectRef, apply]);

  if (!open) {
    return (
      <div className="flex w-8 shrink-0 flex-col items-center border-l border-edge bg-surface pt-1.5">
        <IconButton label="Show inspector" icon={<ChevronIcon size={14} />} onClick={onToggle} />
      </div>
    );
  }

  return (
    <Panel
      role="complementary"
      title="Inspector"
      subtitle={rendered?.panel.label}
      className="w-80 shrink-0 border-l border-edge"
      bodyClassName="flex flex-col"
      padded={false}
      actions={<IconButton size="sm" label="Hide inspector" icon={<ChevronIcon size={13} />} onClick={onToggle} />}
    >
      {rendered ? (
        rendered.content
      ) : (
        <EmptyState
          title="Nothing selected"
          body="Pick an entity in a feature area, or press / to search the document."
        />
      )}
    </Panel>
  );
}
