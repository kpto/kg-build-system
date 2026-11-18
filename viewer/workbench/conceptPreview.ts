import type { ConceptTarget } from "@/lib/concepts";
import { expressionPreview, logicalTypeName } from "@/lib/expressions";
import { relationNamesFromRowSource, resolveAssetName, stepKey } from "@/lib/indexes";
import type { ViewerIndex } from "@/lib/types";
import {
  attachedMeaning,
  type DesignMeaningValue,
} from "@/shared/design/meaning";
import type {
  ConceptPreviewFact,
  ConceptPreviewModel,
} from "@/shared/ui/ConceptPreview";
import { COLLECTIONS, collectionTitle, type CollectionId } from "./collections";

const COLLECTION_IDS = new Set(Object.keys(COLLECTIONS));

function fact(
  label: string,
  value: string | number | null | undefined,
): ConceptPreviewFact | undefined {
  if (value === null || value === undefined) return undefined;
  const text = String(value).trim();
  return text ? { label, value: text } : undefined;
}

function facts(
  ...items: Array<ConceptPreviewFact | undefined>
): ConceptPreviewFact[] {
  return items.filter((item): item is ConceptPreviewFact => Boolean(item));
}

function meaningOrUndefined(
  value: DesignMeaningValue,
): DesignMeaningValue | undefined {
  return value.purpose ||
    value.claims.length ||
    value.limitations.length ||
    (value.frames?.length ?? 0)
    ? value
    : undefined;
}

function propertyParts(
  target: ConceptTarget,
): { component: string; property: string } | undefined {
  if (target.component && target.property) {
    return { component: target.component, property: target.property };
  }
  const cut = target.name.lastIndexOf(".");
  if (cut <= 0 || cut === target.name.length - 1) return undefined;
  return {
    component: target.component ?? target.name.slice(0, cut),
    property: target.property ?? target.name.slice(cut + 1),
  };
}

function collectionFacts(
  index: ViewerIndex,
  id: CollectionId,
): ConceptPreviewFact[] {
  switch (id) {
    case "assets":
      return facts(fact("Items", index.assets.length));
    case "sourceRelations":
      return facts(fact("Items", index.relations.length));
    case "derivedRelations":
      return facts(fact("Items", index.projections.length));
    case "bindings":
      return facts(fact("Items", index.bindings.length));
    case "nodes":
      return facts(
        fact(
          "Items",
          index.topologyNodes.filter((node) => !node.abstract).length,
        ),
      );
    case "abstract":
      return facts(
        fact(
          "Items",
          index.topologyNodes.filter((node) => node.abstract).length +
            index.topologyEdges.filter((edge) => edge.abstract).length,
        ),
      );
    case "edges":
      return facts(
        fact(
          "Items",
          index.topologyEdges.filter((edge) => !edge.abstract).length,
        ),
      );
    case "workflow":
      return facts(
        fact("Components", index.workflow.components.length),
        fact("Steps", index.workflow.steps.length),
      );
  }
}

/** Resolve one concept target to the preview shown on its pill. */
export function previewForConceptTarget(
  index: ViewerIndex,
  target: ConceptTarget,
): ConceptPreviewModel | undefined {
  if (target.collection) {
    if (!COLLECTION_IDS.has(target.collection)) return undefined;
    const id = target.collection as CollectionId;
    return {
      concept: target.concept,
      name: collectionTitle(id, target.component),
      kind: "Collection",
      facts: collectionFacts(index, id),
    };
  }

  switch (target.concept) {
    case "graph": {
      return {
        concept: "graph",
        name: target.name || index.graphDeclaration?.name || "Graph",
        kind: "Graph declaration",
        facts: facts(
          fact("Nodes", index.stats.topologyNodes),
          fact("Edges", index.stats.topologyEdges),
          fact("Assets", index.stats.assets),
          fact("Source relations", index.stats.sourceRelations),
          fact("Derived relations", index.stats.derivedRelations),
          fact("Bindings", index.stats.bindings),
        ),
        meaning: meaningOrUndefined(attachedMeaning(index.graphSemantics)),
      };
    }
    case "node":
    case "abstractNode": {
      const node = index.topologyNodesByName.get(target.name);
      if (!node) return undefined;
      const incident = index.topologyEdges.filter(
        (edge) =>
          edge.source?.[2] === node.name || edge.target?.[2] === node.name,
      ).length;
      return {
        concept: target.concept,
        name: node.name,
        kind: node.abstract ? "Abstract node" : "Node",
        facts: facts(
          fact("Labels", node.labels?.join(" · ")),
          fact("Parent", node.parent?.[2]),
          fact("Properties", node.properties?.length ?? 0),
          fact("Connections", incident),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(node.semantics ?? node.meaning),
        ),
      };
    }
    case "edge":
    case "abstractEdge": {
      const edge = index.topologyEdgesByName.get(target.name);
      if (!edge) return undefined;
      return {
        concept: target.concept,
        name: edge.name,
        kind: edge.abstract ? "Abstract edge" : "Edge",
        facts: facts(
          fact(
            "Endpoints",
            `${edge.source?.[2] ?? "unknown"} → ${
              edge.target?.[2] ?? "unknown"
            }`,
          ),
          fact("Properties", edge.properties?.length ?? 0),
          fact("Labels", edge.labels?.join(" · ")),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(edge.semantics ?? edge.meaning),
        ),
      };
    }
    case "property": {
      const parts = propertyParts(target);
      if (!parts) return undefined;
      const node = index.topologyNodesByName.get(parts.component);
      const edge = index.topologyEdgesByName.get(parts.component);
      const owner = node ?? edge;
      const property = owner?.properties?.find(
        (candidate) => candidate.name === parts.property,
      );
      if (!owner) return undefined;
      return {
        concept: "property",
        name: `${parts.component}.${parts.property}`,
        kind: "Property",
        facts: facts(
          fact("Owner", `${node ? "node" : "edge"} ${parts.component}`),
          fact("Type", logicalTypeName(property?.logical_type)),
          fact("Definition", property?.description),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(property?.semantics ?? property?.meaning),
        ),
      };
    }
    case "asset": {
      const asset = index.assetsByName.get(target.name);
      if (!asset) return undefined;
      const readers = index.relations.filter(
        (relation) => resolveAssetName(index, relation.name) === asset.name,
      ).length;
      return {
        concept: "asset",
        name: asset.name,
        kind: "Asset",
        facts: facts(
          fact("Layout", asset.layout?.kind),
          fact("Location", asset.layout?.locator),
          fact("Version", asset.version),
          fact("Authority", asset.profile?.authority),
          fact("Source relations", readers),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(asset.semantics ?? asset.meaning),
        ),
      };
    }
    case "table": {
      const relation = index.relationByName.get(target.name);
      if (!relation) return undefined;
      return {
        concept: "table",
        name: relation.name,
        kind: "Source relation",
        facts: facts(
          fact("Asset", resolveAssetName(index, relation.name)),
          fact("Columns", relation.columns.length),
          fact("Grain", relation.definition?.grain),
          fact("Identity", relation.definition?.identity?.join(", ")),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(relation.semantics ?? relation.meaning),
        ),
      };
    }
    case "projection": {
      const projection = index.projectionByName.get(target.name);
      if (!projection) return undefined;
      const scans = relationNamesFromRowSource(projection.row_source);
      return {
        concept: "projection",
        name: projection.name,
        kind: "Derived relation",
        facts: facts(
          fact("Scans", scans.join(", ")),
          fact("Columns", projection.columns.length),
          fact("Grain", projection.definition?.grain),
          fact("Identity", projection.definition?.identity?.join(", ")),
          fact("Visibility", projection.visibility),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(projection.semantics ?? projection.meaning),
        ),
      };
    }
    case "field": {
      const fields = [...index.fieldsByKey.values()].filter(
        (candidate) =>
          candidate.field.name === target.name &&
          (!target.component || candidate.ownerName === target.component),
      );
      const field = fields[0];
      if (!field) return undefined;
      const definition = field.field.definition;
      return {
        concept: "field",
        name: field.field.name,
        kind: "Field",
        facts: facts(
          fact("Owner", `${field.ownerKind} ${field.ownerName}`),
          fact("Type", logicalTypeName(field.field.logical_type)),
          fact(
            "Definition",
            definition
              ? [definition.value, definition.unit, definition.null_meaning]
                  .filter(Boolean)
                  .join(" · ")
              : field.field.description,
          ),
          fact("Expression", expressionPreview(field.field.expression)),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(field.field.semantics ?? field.field.meaning),
        ),
      };
    }
    case "binding": {
      const binding =
        target.bindingIndex !== undefined
          ? index.bindings.find(
              (candidate) => candidate.index === target.bindingIndex,
            )
          : index.bindings.find(
              (candidate) =>
                candidate.component === target.component &&
                (candidate.binding.name === target.name ||
                  `binding #${candidate.index}` === target.name),
            );
      if (!binding) return undefined;
      const rows = relationNamesFromRowSource(binding.binding.rows);
      return {
        concept: "binding",
        name: binding.binding.name ?? `binding #${binding.index}`,
        kind: "Binding",
        facts: facts(
          fact("Target", `${binding.kind} ${binding.component}`),
          fact("Rows read", rows.join(", ") || "no row source"),
          fact("Step", binding.step?.id[1]),
          fact(
            "Properties",
            Object.keys(binding.binding.properties ?? {}).length,
          ),
        ),
        meaning: meaningOrUndefined(
          attachedMeaning(binding.binding.semantics ?? binding.binding.meaning),
        ),
      };
    }
    case "step": {
      const stepId =
        target.stepId ??
        (target.component && target.name
          ? [target.component, target.name]
          : undefined);
      const step = stepId
        ? index.stepsById.get(stepKey(stepId))
        : undefined;
      if (!step) return undefined;
      const bindings = index.bindings.filter(
        (candidate) => candidate.step?.id.join("/") === step.id.join("/"),
      ).length;
      return {
        concept: "step",
        name: step.id[1],
        kind: "Step",
        facts: facts(
          fact("Component", step.id[0]),
          fact("Instruction", step.instruction.kind.join(" · ")),
          fact("Inputs", step.inputs?.length ?? 0),
          fact("Outputs", step.outputs?.length ?? 0),
          fact("Bindings", bindings),
        ),
      };
    }
    case "workflow": {
      const component = index.componentsById.get(
        target.component ?? target.name,
      );
      if (!component) return undefined;
      const steps = index.stepsByComponent.get(component.id)?.length ?? 0;
      return {
        concept: "workflow",
        name: component.id,
        kind: "Workflow component",
        facts: facts(
          fact("Steps", steps),
          fact("Version", component.version),
          fact("Runtime fields", component.runtime_fields?.length ?? 0),
        ),
      };
    }
    case "semantics": {
      const subject = [...index.semanticsByKey.values()].find(
        (candidate) =>
          candidate.name === target.name &&
          (!target.component || candidate.ownerName === target.component),
      );
      if (!subject) return undefined;
      return {
        concept: "semantics",
        name: subject.name,
        kind: "Meaning",
        facts: facts(
          fact("Owner", subject.ownerName),
          fact("Entity", subject.entityKind),
        ),
        meaning: meaningOrUndefined(attachedMeaning(subject.semantics)),
      };
    }
  }
}
