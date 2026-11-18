import { artifactKey, resolveAssetName, stepKey } from "@/lib/indexes";
import type {
  EntityKind,
  Ref,
  ViewerIndex,
  WorkflowStep,
} from "@/lib/types";
import type { ProofModel } from "@/proof/model";
import { narrowedWorkflowRows } from "@/proof/workflow";
import type { SubjectSelection } from "@/workbench/types";
import {
  buildWorkflowModel,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";

/**
 * Resolve the workflow steps that participate in one concept.
 *
 * A record is read through its lineage, so the steps that produce its source
 * relations, bindings and graph artifacts are all involved. A declaration or
 * artifact resolves to the steps that produce its artifact and the immediate
 * neighbours the plan connects to it. A collection aggregates its members. The
 * result stays in workflow order.
 */
export function involvedWorkflowRows(
  index: ViewerIndex,
  selection: SubjectSelection | undefined,
  model?: ProofModel,
): WorkflowStepRow[] {
  if (!selection) return [];
  const keys = new Set<string>();

  const add = (step: WorkflowStep | undefined) => {
    if (step) keys.add(stepKey(step.id));
  };

  const addNeighbours = (step: WorkflowStep | undefined) => {
    add(step);
    if (!step) return;
    const key = stepKey(step.id);
    for (const connection of index.incomingByStepId.get(key) ?? []) {
      add(index.stepsById.get(stepKey(connection.outputStepId)));
    }
    for (const connection of index.outgoingByStepId.get(key) ?? []) {
      add(index.stepsById.get(stepKey(connection.inputStepId)));
    }
  };

  const addArtifact = (type: string[], neighbours = true) => {
    for (const step of index.producersByArtifactKey.get(artifactKey(type)) ?? []) {
      if (neighbours) addNeighbours(step);
      else add(step);
    }
  };

  const addRecord = (kind: EntityKind, component: string) => {
    addArtifact(["core", "graph", kind, component]);
    for (const binding of index.bindings) {
      if (binding.kind === kind && binding.component === component) {
        addNeighbours(binding.step);
      }
    }
  };

  const addRelation = (kind: "relation" | "projection", name: string) => {
    addArtifact(
      kind === "relation"
        ? ["core", "data", "table", name]
        : ["core", "data", "derived_relation", name],
    );
  };

  const addAsset = (name: string) => {
    for (const relation of index.relations) {
      if (resolveAssetName(index, relation.name) !== name) continue;
      addArtifact(["core", "data", "table", relation.name], false);
    }
    for (const projection of index.projections) {
      if (resolveAssetName(index, projection.name) !== name) continue;
      addArtifact(
        ["core", "data", "derived_relation", projection.name],
        false,
      );
    }
  };

  const underAbstract = (parent: Ref | undefined, name: string): boolean => {
    let current = parent;
    const seen = new Set<string>();
    while (current) {
      const parentName = current[2];
      if (!parentName || seen.has(parentName)) return false;
      if (parentName === name) return true;
      seen.add(parentName);
      const next =
        index.topologyNodesByName.get(parentName) ??
        index.topologyEdgesByName.get(parentName);
      current = next?.parent;
    }
    return false;
  };

  const addAbstract = (name: string) => {
    for (const node of index.topologyNodes) {
      if (node.abstract || !underAbstract(node.parent, name)) continue;
      addRecord("node", node.name);
    }
    for (const edge of index.topologyEdges) {
      if (edge.abstract || !underAbstract(edge.parent, name)) continue;
      addRecord("edge", edge.name);
    }
  };

  const addCollection = () => {
    const id = selection.collection ?? "assets";
    if (id === "assets") {
      for (const asset of index.assets) addAsset(asset.name);
      return;
    }
    if (id === "sourceRelations") {
      for (const relation of index.relations) {
        addRelation("relation", relation.name);
      }
      return;
    }
    if (id === "derivedRelations") {
      for (const projection of index.projections) {
        addRelation("projection", projection.name);
      }
      return;
    }
    if (id === "nodes") {
      for (const node of index.topologyNodes) {
        if (!node.abstract) addRecord("node", node.name);
      }
      return;
    }
    if (id === "edges") {
      for (const edge of index.topologyEdges) {
        if (!edge.abstract) addRecord("edge", edge.name);
      }
      return;
    }
    if (id === "abstract") {
      for (const node of index.topologyNodes) {
        if (node.abstract) addAbstract(node.name);
      }
      for (const edge of index.topologyEdges) {
        if (edge.abstract) addAbstract(edge.name);
      }
      return;
    }
    if (id === "bindings") {
      for (const binding of index.bindings) addNeighbours(binding.step);
      return;
    }
    const steps = selection.component
      ? (index.stepsByComponent.get(selection.component) ?? [])
      : (index.workflow.steps ?? []);
    for (const step of steps) add(step);
  };

  if (model) {
    if (
      model.level === "property" ||
      model.level === "node" ||
      model.level === "edge"
    ) {
      return narrowedWorkflowRows(index, model);
    }
    if (model.level === "asset") {
      addAsset(model.subject.component);
    } else if (model.level === "abstract") {
      addAbstract(model.subject.component);
    }
  } else {
    switch (selection.kind) {
      case "graph":
        for (const step of index.workflow.steps ?? []) {
          if (
            step.outputs?.some(
              (output) =>
                output.type?.[0] === "core" && output.type?.[1] === "graph",
            )
          ) {
            add(step);
          }
        }
        break;
      case "node":
      case "edge": {
        const component = selection.component ?? selection.name;
        if (!component) break;
        if (selection.level === "abstract" || selection.abstract) {
          addAbstract(component);
        } else {
          addRecord(selection.kind, component);
        }
        break;
      }
      case "property": {
        const component = selection.component ?? selection.name;
        if (!component) break;
        const kind: EntityKind = index.topologyNodesByName.has(component)
          ? "node"
          : "edge";
        addRecord(kind, component);
        break;
      }
      case "asset": {
        const component = selection.component ?? selection.name;
        if (component) addAsset(component);
        break;
      }
      case "relation":
      case "projection": {
        const component = selection.component ?? selection.name;
        if (component) addRelation(selection.kind, component);
        break;
      }
      case "binding": {
        const binding = index.bindings.find(
          (candidate) => candidate.index === selection.bindingIndex,
        );

        addNeighbours(binding?.step);
        break;
      }
      case "step": {
        const step = selection.stepId
          ? index.stepsById.get(stepKey(selection.stepId))
          : undefined;
        addNeighbours(step);
        break;
      }
      case "collection":
        addCollection();
        break;
      default:
        break;
    }
  }

  return buildWorkflowModel(index).rows.filter((row) => keys.has(row.key));
}
