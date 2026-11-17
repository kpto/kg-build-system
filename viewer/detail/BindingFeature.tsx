"use client";

import { useMemo } from "react";

import { collectFieldRefs } from "@/lib/expressions";
import {
  artifactDisplay,
  relationNamesFromRowSource,
  stepKey,
} from "@/lib/indexes";
import type { IndexedBinding, ViewerIndex } from "@/lib/types";
import type { ProvenanceReferences } from "@/proof/references";
import {
  EdgePill,
  NodePill,
  StepPill,
} from "@/detail/view/ConceptPill";
import { Constitution } from "@/detail/view/Constitution";
import { constitutionModel } from "@/detail/model/constitution";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import { attachedMeaning } from "@/shared/design/meaning";
import { activeDocument, documentSelection, type WorkspaceProps } from "@/workbench/types";
import {
  buildWorkflowModel,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import {
  DetailBand,
  DetailDocument,
  DetailEmptyState,
  type DetailFact,
} from "./view/DetailChrome";
import {
  ExpressionTree,
  type ExpressionChain,
} from "./view/ExpressionTree";
import { WorkflowProvenanceGraph } from "./view/WorkflowProvenanceGraph";

const EMPTY_REFERENCES: ProvenanceReferences = {
  assets: [],
  tables: [],
  projections: [],
};

function bindingTitle(binding: IndexedBinding): string {
  return binding.binding.name ?? `binding #${binding.index}`;
}

function identityFields(binding: IndexedBinding): string[] {
  return [
    ...new Set(
      collectFieldRefs(binding.binding.identity)
        .map((ref) => ref[ref.length - 1])
        .filter(Boolean),
    ),
  ];
}

function bindingExpressionChains(binding: IndexedBinding): ExpressionChain[] {
  const chains: ExpressionChain[] = [];
  const add = (
    id: string,
    target: ExpressionChain["target"],
    expression: ExpressionChain["expression"],
  ) => {
    if (expression) chains.push({ id, target, expression });
  };

  add(
    "identity",
    {
      concept: binding.kind,
      label: binding.component,
      detail: "identity expression",
    },
    binding.binding.identity,
  );
  if (binding.kind === "edge") {
    add(
      "source-identity",
      {
        concept: "edge",
        label: `${binding.component}.source`,
        detail: "source identity",
      },
      binding.binding.source_identity,
    );
    add(
      "target-identity",
      {
        concept: "edge",
        label: `${binding.component}.target`,
        detail: "target identity",
      },
      binding.binding.target_identity,
    );
  }
  for (const [property, expression] of Object.entries(
    binding.binding.properties ?? {},
  )) {
    add(
      `property:${property}`,
      {
        concept: "property",
        label: `${binding.component}.${property}`,
        detail: "binding property",
      },
      expression,
    );
  }
  return chains;
}

/** The binding step and the steps it reads from and writes to. */
function bindingWorkflowRows(
  index: ViewerIndex,
  binding: IndexedBinding,
): WorkflowStepRow[] {
  if (!binding.step) return [];
  const key = stepKey(binding.step.id);
  const keys = new Set<string>([key]);
  for (const connection of index.incomingByStepId.get(key) ?? []) {
    keys.add(stepKey(connection.outputStepId));
  }
  for (const connection of index.outgoingByStepId.get(key) ?? []) {
    keys.add(stepKey(connection.inputStepId));
  }
  return buildWorkflowModel(index).rows.filter((row) => keys.has(row.key));
}

/** One binding as its own document: what it writes and how it is built. */
export function BindingEditor(props: WorkspaceProps) {
  const { index } = props.state;
  const selection = documentSelection(activeDocument(props.state));
  const binding = useMemo(
    () =>
      selection?.kind === "binding" && selection.bindingIndex !== undefined
        ? index.bindings.find(
            (candidate) => candidate.index === selection.bindingIndex,
          )
        : undefined,
    [index.bindings, selection],
  );
  const constitution = useMemo(
    () =>
      binding
        ? constitutionModel(index, {
            level: "binding",
            component: binding.component,
            bindingIndex: binding.index,
          })
        : undefined,
    [binding, index],
  );

  if (!binding) {
    return (
      <DetailDocument
        testId="binding-editor"
        concept="binding"
        kicker="Binding"
        title="Binding unavailable"
        subtitle="This binding is not present in the blueprint."
      >
        <DetailBand
          title="Binding"
          question="Which binding is this?"
        >
          <DetailEmptyState>
            The selected binding could not be resolved from the snapshot.
          </DetailEmptyState>
        </DetailBand>
      </DetailDocument>
    );
  }

  const meaning = attachedMeaning(
    binding.binding.meaning ?? binding.binding.semantics,
  );
  const hasMeaning =
    Boolean(meaning.purpose) ||
    meaning.claims.length > 0 ||
    meaning.limitations.length > 0 ||
    (meaning.frames?.length ?? 0) > 0;
  const chains = bindingExpressionChains(binding);
  const rows = bindingWorkflowRows(index, binding);
  const relations = relationNamesFromRowSource(binding.binding.rows);
  const written = Object.keys(binding.binding.properties ?? {});
  const identity = identityFields(binding);
  const title = bindingTitle(binding);

  const facts: DetailFact[] = [
    {
      label: "Record",
      value:
        binding.kind === "node" ? (
          <NodePill name={binding.component} />
        ) : (
          <EdgePill name={binding.component} />
        ),
    },
    { label: "Writes", value: `${written.length}` },
    {
      label: "Identity",
      value: identity.join(", ") || "not declared",
      absent: !identity.length,
      wrap: true,
    },
    {
      label: "Rows",
      value: relations.join(", ") || "no row source",
      title: relations.join(" · "),
      absent: !relations.length,
    },
    {
      label: "Step",
      value: binding.step ? (
        <StepPill
          name={binding.step.id[1]}
          component={binding.step.id[0]}
          stepId={binding.step.id}
          title={binding.step.id.join(".")}
        />
      ) : (
        "no build step"
      ),
      absent: !binding.step,
    },
    {
      label: "Output",
      value: artifactDisplay(binding.outputArtifact),
      title: artifactDisplay(binding.outputArtifact),
    },
  ];

  return (
    <DetailDocument
      testId="binding-editor"
      concept="binding"
      kicker="Binding"
      title={title}
      subtitle={binding.binding.mode}
      facts={facts}
    >
      {hasMeaning ? (
        <DetailBand
          concept="semantics"
          title="Meaning"
          question="What does this binding fulfil, and what does it exclude?"
          testId="binding-meaning"
        >
          <DesignMeaning
            {...meaning}
            emptyText="Meaning omitted for this binding."
          />
        </DetailBand>
      ) : null}

      {constitution ? (
        <DetailBand
          concept="semantics"
          title="Constitution"
          question="What is this binding for, and how does it come to be?"
          testId="detail-constitution"
        >
          <Constitution model={constitution} />
        </DetailBand>
      ) : null}

      {chains.length ? (
        <ExpressionTree
          index={index}
          references={EMPTY_REFERENCES}
          chains={chains}
          item={{ concept: "binding", label: title }}
        />
      ) : (
        <DetailBand
          concept="graph"
          title="Expression"
          question="Which fields and operations produce the value?"
        >
          <DetailEmptyState>
            No expression is declared for this binding.
          </DetailEmptyState>
        </DetailBand>
      )}

      <WorkflowProvenanceGraph
        index={index}
        rows={rows}
        onOpenStep={(row) =>
          props.actions.openTab({
            selection: {
              kind: "step",
              component: row.component,
              name: row.name,
              stepId: row.id,
            },
          })
        }
      />
    </DetailDocument>
  );
}
