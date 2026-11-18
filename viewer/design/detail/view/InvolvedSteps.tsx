"use client";

/**
 * The universal last card: the workflow steps involved in one concept drawn as
 * the same DAG the Workflow document uses. The rows are narrowed to this
 * concept, so the card is a focused subset of the workflow tab.
 */

import { useCallback, useMemo, useState } from "react";

import type { ViewerIndex } from "@/lib/types";
import type { ProofModel } from "@/proof/model";
import { useConceptNavigation } from "@/shared/ui/ConceptNavigation";
import { groupPalette } from "@/shared/ui/theme";
import { ViewportHint } from "@/shared/ui/Viewport";
import {
  WorkflowDag,
  buildStepComponentScene,
  buildStepScene,
  type WorkflowDagNode,
} from "@/shared/ui/WorkflowDag";
import type { SubjectSelection } from "@/workbench/types";
import type { WorkflowStepRow } from "@/workflow/model/WorkflowViewModel";
import { involvedWorkflowRows } from "../model/involvedSteps";
import { DetailBand } from "./DetailChrome";
import styles from "../detail.module.css";

export function InvolvedSteps({
  index,
  selection,
  model,
  rows,
}: {
  index: ViewerIndex;
  selection?: SubjectSelection;
  model?: ProofModel;
  rows?: WorkflowStepRow[];
}) {
  const resolved = useMemo(
    () => rows ?? involvedWorkflowRows(index, selection, model),
    [rows, index, selection, model],
  );
  const [selectedId, setSelectedId] = useState<string>();
  const navigation = useConceptNavigation();
  const components = useMemo(
    () => [...new Set(resolved.map((row) => row.component))],
    [resolved],
  );
  const tintFor = useCallback(
    (component: string) =>
      groupPalette[Math.max(0, components.indexOf(component)) % groupPalette.length],
    [components],
  );
  // A handful of steps stays a step DAG; a large subset collapses to its
  // components so the same card remains readable instead of a tiny strip.
  const grouped = resolved.length > 16;
  const scene = useMemo(() => {
    if (!resolved.length) return undefined;
    if (grouped) return buildStepComponentScene(index, resolved);
    return buildStepScene(index, "", resolved, tintFor, {
      boundaries: false,
    });
  }, [grouped, index, resolved, tintFor]);
  const fitKey = `${selection?.kind ?? ""}:${selection?.component ?? ""}:${
    selection?.property ?? ""
  }:${resolved.length}:${grouped ? "components" : "steps"}`;

  const openStep = (node: WorkflowDagNode) => {
    if (!node.row || !navigation) return;
    navigation.open({
      concept: "step",
      name: node.row.name,
      component: node.row.component,
      stepId: node.row.id,
    });
  };

  return (
    <DetailBand
      title="Involved steps"
      question="Which build steps participate in this concept?"
      testId="detail-involved-steps"
    >
      {scene ? (
        <>
          <p className={styles.involvedCount}>
            {resolved.length} {resolved.length === 1 ? "step" : "steps"}
            {grouped
              ? ` · ${components.length} ${
                  components.length === 1 ? "component" : "components"
                }`
              : ""}
          </p>
          <div className={styles.involvedDag}>
            <WorkflowDag
              scene={scene}
              selectedId={selectedId}
              onSelect={(node) => setSelectedId(node.id)}
              onOpen={openStep}
              onBackgroundClick={() => setSelectedId(undefined)}
              className={styles.involvedDagCanvas}
              testId="involved-workflow-dag"
              ariaLabel={
                grouped
                  ? `Involved workflow with ${resolved.length} steps in ${components.length} components`
                  : `Involved workflow with ${resolved.length} steps`
              }
              fitKey={fitKey}
            />
            <ViewportHint className="pointer-events-none">
              {grouped ? "pan · zoom" : "pan · zoom · open step"}
            </ViewportHint>
          </div>
        </>
      ) : (
        <p className={styles.inlineEmpty}>
          No workflow steps resolve to this concept.
        </p>
      )}
    </DetailBand>
  );
}
