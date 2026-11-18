"use client";

/**
 * One shared last card for every concept: the workflow steps involved in it.
 *
 * The caller may pass rows it already resolved; otherwise the card resolves
 * the concept through the same involved-step rules. A step pill opens its own
 * document, so the card never carries a click handler of its own.
 */

import { useMemo } from "react";

import type { ViewerIndex } from "@/lib/types";
import type { ProofModel } from "@/proof/model";
import type { SubjectSelection } from "@/workbench/types";
import type { WorkflowStepRow } from "@/workflow/model/WorkflowViewModel";
import { involvedWorkflowRows } from "../model/involvedSteps";
import { StepPill } from "./ConceptPill";
import {
  DetailBand,
  MemberTable,
  type MemberRow,
} from "./DetailChrome";
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
  const memberRows: MemberRow[] = resolved.map((row) => ({
    key: row.key,
    title: `${row.id.join(".")} · ${row.kindLabel}`,
    cells: [
      <StepPill
        key="step"
        name={row.name}
        component={row.component}
        stepId={row.id}
        title={row.id.join(".")}
      />,
      row.component,
      row.kindLabel,
      `${row.connections}`,
    ],
  }));

  return (
    <DetailBand
      title="Involved steps"
      question="Which build steps participate in this concept?"
      testId="detail-involved-steps"
    >
      {memberRows.length ? (
        <p className={styles.involvedCount}>
          {resolved.length} {resolved.length === 1 ? "step" : "steps"}
        </p>
      ) : null}
      <div className={styles.involvedWide}>
        <MemberTable
          columns={["Step", "Component", "Instruction", "Links"]}
          template="minmax(170px, 1.5fr) minmax(90px, 0.8fr) minmax(120px, 1.1fr) 56px"
          rows={memberRows}
          empty="No workflow steps resolve to this concept."
          testId="involved-steps-table"
        />
      </div>
      <div className={styles.involvedNarrow} data-testid="involved-steps-list">
        {resolved.length ? (
          resolved.map((row) => (
            <div key={row.key} className={styles.involvedRow}>
              <StepPill
                name={row.name}
                component={row.component}
                stepId={row.id}
                title={row.id.join(".")}
              />
              <span className={styles.involvedLinks}>{row.connections}</span>
              <span className={styles.involvedMeta}>
                {row.component} · {row.kindLabel}
              </span>
            </div>
          ))
        ) : (
          <p className={styles.inlineEmpty}>
            No workflow steps resolve to this concept.
          </p>
        )}
      </div>
    </DetailBand>
  );
}
