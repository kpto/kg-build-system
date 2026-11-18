import { stepKey } from "@/lib/indexes";
import { buildLineage, propertySelection } from "@/lib/lineage";
import type { ViewerIndex, WorkflowStep } from "@/lib/types";
import {
  buildWorkflowModel,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import type { ProofModel } from "./model";

function collectBranch(branch: ReturnType<typeof buildLineage>["branches"][number], add: (step?: WorkflowStep) => void) {
  add(branch.bindingStep);
  branch.sourceSteps.forEach(add);
  branch.transformationSteps.forEach(add);
  branch.postSteps.forEach(add);
  branch.targetSteps.forEach(add);
}

/**
 * The workflow steps that produce a node, edge or property. The property path
 * reads the branches already built for the document; the component path builds
 * the same branches for each property and adds the binding neighbourhood for
 * subjects whose provenance is carried only by identity expressions.
 */
export function narrowedWorkflowRows(
  index: ViewerIndex,
  model: ProofModel,
): WorkflowStepRow[] {
  if (model.level !== "property" && model.level !== "node" && model.level !== "edge") {
    return [];
  }

  const keys = new Set<string>();
  const add = (step?: WorkflowStep) => {
    if (step) keys.add(stepKey(step.id));
  };
  const addStepId = (id?: [string, string]) => {
    if (!id) return;
    add(index.stepsById.get(stepKey(id)));
  };

  if (model.level === "property") {
    for (const branch of model.branches) {
      collectBranch(branch.branch, add);
    }
  } else {
    const kind = model.level;
    const component = model.subject.component;
    for (const property of model.component?.properties ?? []) {
      const lineage = buildLineage(
        index,
        propertySelection(kind, component, property.property),
      );
      for (const branch of lineage.branches) collectBranch(branch, add);
    }
    for (const binding of index.bindings) {
      if (binding.kind !== kind || binding.component !== component) continue;
      add(binding.step);
      if (!binding.step) continue;
      const key = stepKey(binding.step.id);
      for (const connection of index.incomingByStepId.get(key) ?? []) {
        addStepId(connection.outputStepId);
      }
      for (const connection of index.outgoingByStepId.get(key) ?? []) {
        addStepId(connection.inputStepId);
      }
    }
  }

  return buildWorkflowModel(index).rows.filter((row) => keys.has(row.key));
}
