"use client";

import { useMemo, useState } from "react";

import type { ViewerIndex } from "@/lib/types";
import type { ProofModel } from "@/proof/model";
import { narrowedWorkflowRows } from "@/proof/workflow";
import { DetailPanel } from "@/detail/view/DetailChrome";
import { GraphCanvas } from "@/shared/ui/GraphCanvas";
import { groupPalette } from "@/shared/ui/theme";
import {
  WorkflowGraphSceneView,
  buildStepScene,
} from "@/workflow/view/WorkflowGraph";
import type { WorkflowStepRow } from "@/workflow/model/WorkflowViewModel";
import styles from "../detail.module.css";

export function WorkflowProvenanceGraph({
  index,
  model,
  onOpenStep,
}: {
  index: ViewerIndex;
  model: ProofModel;
  onOpenStep(row: WorkflowStepRow): void;
}) {
  const rows = useMemo(
    () => narrowedWorkflowRows(index, model),
    [index, model],
  );
  const [selectedId, setSelectedId] = useState<string>();
  const scene = useMemo(() => {
    if (!rows.length) return undefined;
    const components = [...new Set(rows.map((row) => row.component))];
    const tintFor = (component: string) => {
      const position = components.indexOf(component);
      return groupPalette[Math.max(0, position) % groupPalette.length];
    };
    return buildStepScene(index, "", rows, tintFor);
  }, [index, rows]);

  if (!rows.length || !scene) {
    return (
      <DetailPanel concept="workflow" title="Workflow" meta="0 steps">
        <p className={styles.workflowEmpty}>
          No workflow steps resolve to this subject.
        </p>
      </DetailPanel>
    );
  }

  return (
    <DetailPanel
      concept="workflow"
      title="Workflow"
      meta={`${rows.length} steps · ${scene.stats?.internalEdges ?? 0} links`}
    >
      <GraphCanvas
        width={scene.width}
        height={scene.height}
        className={styles.workflowGraph}
        testId="detail-workflow-graph"
        ariaLabel={`Narrowed workflow graph with ${rows.length} steps`}
        onBackgroundClick={() => setSelectedId(undefined)}
      >
        <WorkflowGraphSceneView
          scene={scene}
          selectedId={selectedId}
          onSelect={(node) => {
            if (node.kind === "step") setSelectedId(node.id);
          }}
          onOpen={(node) => {
            if (node.row) onOpenStep(node.row);
          }}
        />
      </GraphCanvas>
      <p className={styles.workflowHint}>
        Click a step to select; double-click to open its document.
      </p>
    </DetailPanel>
  );
}
