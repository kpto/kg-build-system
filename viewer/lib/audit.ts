/**
 * Deterministic audit engine.
 *
 * Every finding is a statement about the loaded snapshot with at least one
 * artifact pointer. The engine never executes a build, never reads a clock and
 * never calls a model. Findings are observations, not proof of correctness.
 *
 * The health score is a weighted rubric, not a confidence number:
 *
 *   score = round(sum(component.value * component.weight))
 *
 * `value` is a raw percentage in 0..100 for that rubric dimension and `weight`
 * is its share (the weights sum to 1). The UI must show the components so a
 * reviewer can recompute the score by hand.
 */

import type {
  EntityKind,
  Expression,
  IndexedBinding,
  TopologyProperty,
  ViewerIndex,
  WorkflowStep,
} from "./types";
import type {
  AuditFinding,
  AuditReport,
  AuditScoreComponent,
  AuditSubject,
  EvidenceRef,
  ReviewSidecar,
  Severity,
} from "./reviewTypes";
import {
  findComponentPropertyBindings,
  openingMatchesStep,
  relationNamesFromRowSource,
  resolveAssetName,
  stepKey,
} from "./indexes";
import {
  collectFieldRefs,
  expressionPreview,
  fieldRefKey,
  walkExpression,
} from "./expressions";
import { buildLineage, propertySelection } from "./lineage";

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];

const TERMINAL_COMPONENTS = new Set(["file", "meta_graph", "neo4j"]);

const FALLBACK_OPERATORS = new Set(["coalesce", "default_to"]);

type PropertyEntry = {
  kind: EntityKind;
  component: string;
  property: TopologyProperty;
  componentPointer: string;
  propertyPointer: string;
  abstract: boolean;
};

function pointerSegment(value: string): string {
  return value.replace(/~/g, "~0").replace(/\//g, "~1");
}

function evidence(
  label: string,
  artifact: EvidenceRef["artifact"],
  jsonPointer: string,
  ref?: string[],
): EvidenceRef {
  return ref ? { label, artifact, jsonPointer, ref } : { label, artifact, jsonPointer };
}

/** FNV-1a over a string; stable across processes and platforms. */
function stableHash(value: string): string {
  let hash = 0x811c9dc5;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function subjectKey(subject: AuditSubject | undefined): string {
  if (!subject) return "";
  return [
    subject.kind,
    subject.name,
    subject.component ?? "",
    subject.property ?? "",
    subject.entityKind ?? "",
    subject.bindingIndex ?? "",
    subject.stepId?.join("/") ?? "",
  ].join("|");
}

function stableFindingId(
  rule: string,
  subject: AuditSubject | undefined,
  evidenceRefs: readonly EvidenceRef[],
): string {
  const pointers = evidenceRefs
    .map((entry) => `${entry.artifact}:${entry.jsonPointer}`)
    .join("|");
  return `finding:${rule}:${stableHash(`${rule}|${subjectKey(subject)}|${pointers}`)}`;
}

function stableValue(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) sorted[key] = stableValue(record[key]);
    return sorted;
  }
  return value;
}

function stableStringify(value: unknown): string {
  try {
    return JSON.stringify(stableValue(value));
  } catch {
    return String(value);
  }
}

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function hasAnnotations(value: { annotations?: unknown } | undefined): boolean {
  return Boolean(value && Array.isArray(value.annotations) && value.annotations.length > 0);
}

function hasDocumentation(value: {
  description?: unknown;
  annotations?: unknown;
} | undefined): boolean {
  return Boolean(value && (nonEmpty(value.description) || hasAnnotations(value)));
}

function assetHasDocumentation(asset: {
  description?: unknown;
  annotations?: unknown;
  semantics?: {
    subject?: unknown;
    coverage?: unknown;
    authority?: unknown;
    basis?: unknown;
    title?: unknown;
    description?: unknown;
    claims?: unknown[];
    limitations?: unknown[];
  };
}): boolean {
  if (hasDocumentation(asset)) return true;
  const semantics = asset.semantics;
  if (!semantics) return false;
  return (
    nonEmpty(semantics.subject) ||
    nonEmpty(semantics.coverage) ||
    nonEmpty(semantics.authority) ||
    nonEmpty(semantics.basis) ||
    nonEmpty(semantics.title) ||
    nonEmpty(semantics.description) ||
    Boolean(semantics.claims?.length) ||
    Boolean(semantics.limitations?.length)
  );
}

function isNullableLogicalType(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  return (value as { kind?: unknown }).kind === "nullable";
}

function expressionIsNullable(expression: Expression | undefined): boolean {
  if (!expression) return false;
  return isNullableLogicalType(expression.logical_type);
}

function expressionNarrowsNull(expression: Expression | undefined): boolean {
  let narrowed = false;
  walkExpression(expression, (node) => {
    if (node.kind === "operation" && node.operator.at(-1) === "drop_null") {
      narrowed = true;
    }
  });
  return narrowed;
}

function fallbackLiterals(expression: Expression | undefined): unknown[] {
  const values: unknown[] = [];
  walkExpression(expression, (node) => {
    if (node.kind !== "operation") return;
    if (!FALLBACK_OPERATORS.has(node.operator.at(-1) ?? "")) return;
    for (const argument of node.arguments ?? []) {
      if (argument.kind === "literal") values.push(argument.value);
    }
  });
  return values;
}

function formatLiteral(value: unknown): string {
  if (typeof value === "string") return value;
  if (value === null) return "null";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function topologyEntries(index: ViewerIndex): PropertyEntry[] {
  const entries: PropertyEntry[] = [];
  (index.blueprint.graph?.nodes ?? []).forEach((node, nodeIndex) => {
    (node.properties ?? []).forEach((property, propertyIndex) => {
      entries.push({
        kind: "node",
        component: node.name,
        property,
        componentPointer: `/graph/nodes/${nodeIndex}`,
        propertyPointer: `/graph/nodes/${nodeIndex}/properties/${propertyIndex}`,
        abstract: node.abstract === true,
      });
    });
  });
  (index.blueprint.graph?.edges ?? []).forEach((edge, edgeIndex) => {
    (edge.properties ?? []).forEach((property, propertyIndex) => {
      entries.push({
        kind: "edge",
        component: edge.name,
        property,
        componentPointer: `/graph/edges/${edgeIndex}`,
        propertyPointer: `/graph/edges/${edgeIndex}/properties/${propertyIndex}`,
        abstract: edge.abstract === true,
      });
    });
  });
  return entries;
}

function bindingPointer(index: number): string {
  return `/bindings/${index}`;
}

function bindingPropertyPointer(index: number, property: string): string {
  return `/bindings/${index}/properties/${pointerSegment(property)}`;
}

function stepIndex(index: ViewerIndex, step: WorkflowStep | undefined): number {
  return step ? index.workflow.steps.indexOf(step) : -1;
}

function stepSubject(step: WorkflowStep): AuditSubject {
  return {
    kind: "step",
    name: `${step.id[0]}/${step.id[1]}`,
    component: step.id[0],
    stepId: step.id,
  };
}

function bindingSignature(binding: IndexedBinding): string {
  const relations = [...relationNamesFromRowSource(binding.binding.rows)].sort();
  const shape = stableStringify({
    identity: binding.binding.identity ?? null,
    sourceIdentity: binding.binding.source_identity ?? null,
    targetIdentity: binding.binding.target_identity ?? null,
    properties: binding.binding.properties ?? {},
  });
  return `${relations.join("|")}::${shape}`;
}

function failureText(failure: unknown): string {
  if (typeof failure === "string") return failure;
  if (failure && typeof failure === "object") {
    const record = failure as Record<string, unknown>;
    for (const key of ["message", "detail", "error", "reason"]) {
      if (typeof record[key] === "string") return record[key] as string;
    }
    return stableStringify(failure).slice(0, 300);
  }
  return String(failure);
}

function failureSubject(failure: unknown): AuditSubject | undefined {
  if (!failure || typeof failure !== "object") return undefined;
  const record = failure as Record<string, unknown>;
  const component =
    typeof record.component === "string" ? record.component : undefined;
  const step = typeof record.step === "string" ? record.step : undefined;
  if (!component && !step) return undefined;
  return {
    kind: "step",
    name: step ? `${component ?? ""}/${step}` : String(component),
    ...(component ? { component } : {}),
    ...(step ? { stepId: [component ?? "", step] as [string, string] } : {}),
  };
}

function readVersionMap(
  provenance: Record<string, unknown> | null | undefined,
): Record<string, unknown> | undefined {
  if (!provenance) return undefined;
  for (const key of ["component_versions", "componentVersions", "versions", "components"]) {
    const value = provenance[key];
    if (value && typeof value === "object" && !Array.isArray(value)) {
      return value as Record<string, unknown>;
    }
  }
  return undefined;
}

function percentage(value: number, total: number): number {
  return total > 0 ? (value / total) * 100 : 100;
}

function rounded(value: number): number {
  return Math.round(value * 10) / 10;
}

/**
 * Build the audit report for a loaded snapshot.
 *
 * `review` only contributes open design decisions: they become review questions
 * with the sidecar's own evidence. No sidecar claim is promoted to a finding
 * that the snapshot itself does not support.
 */
export function buildAudit(index: ViewerIndex, review?: ReviewSidecar): AuditReport {
  const findings = new Map<string, AuditFinding>();
  const push = (draft: Omit<AuditFinding, "id">): void => {
    const id = stableFindingId(draft.rule, draft.subject, draft.evidence);
    if (!findings.has(id)) findings.set(id, { ...draft, id });
  };

  const entries = topologyEntries(index);

  // -----------------------------------------------------------------------
  // Property-level rules
  // -----------------------------------------------------------------------

  for (const entry of entries) {
    const propertyEntries = findComponentPropertyBindings(
      index,
      entry.kind,
      entry.component,
      entry.property.name,
    );

    // literal-only-property
    const expressions = propertyEntries
      .map((candidate) => candidate.expression)
      .filter((expression): expression is Expression => Boolean(expression));
    if (expressions.length && expressions.every((expression) => collectFieldRefs(expression).length === 0)) {
      const subject: AuditSubject = {
        kind: "property",
        name: entry.component,
        component: entry.component,
        property: entry.property.name,
        entityKind: entry.kind,
        ...(propertyEntries[0] ? { bindingIndex: propertyEntries[0].binding.index } : {}),
      };
      push({
        rule: "literal-only-property",
        severity: "medium",
        title: `Property "${entry.component}.${entry.property.name}" is defined only by literals`,
        detail: `The property has no field reference to a source relation: ${expressions
          .map((expression) => expressionPreview(expression))
          .join(", ")}.`,
        subject,
        evidence: [
          evidence(
            "property declaration",
            "blueprint",
            entry.propertyPointer,
            entry.property.ref,
          ),
          ...propertyEntries.map((candidate) =>
            evidence(
              `binding ${candidate.binding.index} property expression`,
              "blueprint",
              bindingPropertyPointer(candidate.binding.index, entry.property.name),
            ),
          ),
        ],
        tags: ["literal", "traceability"],
      });
    }

    // unreachable-lineage. Abstract components are intentionally unbound, so
    // their inherited properties are not reported as broken lineage.
    if (!propertyEntries.length) {
      if (!entry.abstract) {
        push({
          rule: "unreachable-lineage",
          severity: "high",
          title: `Property "${entry.component}.${entry.property.name}" has no binding`,
          detail:
            "No blueprint binding declares an expression for this topology property, so its lineage cannot be resolved.",
          question: `Property "${entry.component}.${entry.property.name}" has no binding. Is the property intentionally unbound, or was its binding omitted?`,
          subject: {
            kind: "property",
            name: entry.component,
            component: entry.component,
            property: entry.property.name,
            entityKind: entry.kind,
          },
          evidence: [
            evidence(
              "property declaration",
              "blueprint",
              entry.propertyPointer,
              entry.property.ref,
            ),
          ],
          tags: ["lineage", "traceability"],
        });
      }
    } else if (!entry.abstract) {
      const hasBindingStep = propertyEntries.some((candidate) => Boolean(candidate.binding.step));
      const hasFieldRefs = propertyEntries.some(
        (candidate) => candidate.fieldRefs.length > 0,
      );
      if (!hasBindingStep) {
        push({
          rule: "unreachable-lineage",
          severity: "high",
          title: `Property "${entry.component}.${entry.property.name}" has no binding step`,
          detail:
            "A blueprint binding exists but no workflow step produces its binding artifact, so the property cannot be traced to a source.",
          question: `Property "${entry.component}.${entry.property.name}" has a binding but no workflow step. Which step is supposed to produce it?`,
          subject: {
            kind: "property",
            name: entry.component,
            component: entry.component,
            property: entry.property.name,
            entityKind: entry.kind,
            bindingIndex: propertyEntries[0].binding.index,
          },
          evidence: propertyEntries.map((candidate) =>
            evidence(
              `binding ${candidate.binding.index}`,
              "blueprint",
              bindingPointer(candidate.binding.index),
            ),
          ),
          tags: ["lineage", "traceability"],
        });
      } else if (hasFieldRefs) {
        const graph = buildLineage(
          index,
          propertySelection(entry.kind, entry.component, entry.property.name),
        );
        const reachable = graph.branches.some(
          (branch) =>
            branch.sourceRelations.length > 0 || branch.sourceSteps.length > 0,
        );
        if (!reachable) {
          push({
            rule: "unreachable-lineage",
            severity: "high",
            title: `Property "${entry.component}.${entry.property.name}" has no path to a source`,
            detail:
              "The property expression references fields but no source relation or source step is reachable through the workflow.",
            question: `Property "${entry.component}.${entry.property.name}" references fields without a reachable source. Where does this value actually come from?`,
            subject: {
              kind: "property",
              name: entry.component,
              component: entry.component,
              property: entry.property.name,
              entityKind: entry.kind,
              bindingIndex: propertyEntries[0].binding.index,
            },
            evidence: propertyEntries.map((candidate) =>
              evidence(
                `binding ${candidate.binding.index} property expression`,
                "blueprint",
                bindingPropertyPointer(candidate.binding.index, entry.property.name),
              ),
            ),
            tags: ["lineage", "traceability"],
          });
        }
      }
    }

    // missing-description for properties
    if (!hasDocumentation(entry.property)) {
      push({
        rule: "missing-description",
        severity: "low",
        title: `Property "${entry.component}.${entry.property.name}" has no description or annotation`,
        detail:
          "The topology property carries neither a description nor an annotation. A reviewer cannot tell what the field means from the snapshot alone.",
        subject: {
          kind: "property",
          name: entry.component,
          component: entry.component,
          property: entry.property.name,
          entityKind: entry.kind,
        },
        evidence: [
          evidence(
            "property declaration",
            "blueprint",
            entry.propertyPointer,
            entry.property.ref,
          ),
        ],
        tags: ["documentation"],
      });
    }
  }

  // -----------------------------------------------------------------------
  // Binding-level rules
  // -----------------------------------------------------------------------

  // A fallback is a property-level observation, not a per-binding one. A
  // multi-source property such as reading.summary is one review item with one
  // evidence ref per contributing binding.
  const fallbacks = new Map<
    string,
    {
      component: string;
      property: string;
      entityKind: EntityKind;
      bindings: Set<number>;
      values: Set<string>;
    }
  >();
  for (const binding of index.bindings) {
    for (const [propertyName, expression] of Object.entries(
      binding.binding.properties ?? {},
    )) {
      const literals = fallbackLiterals(expression);
      if (!literals.length) continue;
      const key = `${binding.component}\u0000${propertyName}\u0000${binding.kind}`;
      const entry = fallbacks.get(key) ?? {
        component: binding.component,
        property: propertyName,
        entityKind: binding.kind,
        bindings: new Set<number>(),
        values: new Set<string>(),
      };
      entry.bindings.add(binding.index);
      for (const literal of literals) entry.values.add(formatLiteral(literal));
      fallbacks.set(key, entry);
    }
  }

  for (const entry of fallbacks.values()) {
    const bindingIndexes = [...entry.bindings].sort((left, right) => left - right);
    const values = [...entry.values].sort();
    const subject: AuditSubject = {
      kind: "property",
      name: entry.component,
      component: entry.component,
      property: entry.property,
      entityKind: entry.entityKind,
      ...(bindingIndexes.length === 1
        ? { bindingIndex: bindingIndexes[0] }
        : {}),
    };
    push({
      rule: "hard-coded-fallback",
      severity: "medium",
      title: `Property "${entry.component}.${entry.property}" falls back to ${values.join(", ")}`,
      detail: `The property supplies hard-coded fallback${values.length === 1 ? "" : "s"} when the source value is absent: ${values.join(", ")}.`,
      question: `Property "${entry.component}.${entry.property}" falls back to ${values.join(", ")} when the source is missing. Is a visible default the intended semantic, or should the property stay absent?`,
      subject,
      evidence: bindingIndexes.map((bindingIndex) =>
        evidence(
          "binding property expression",
          "blueprint",
          bindingPropertyPointer(bindingIndex, entry.property),
        ),
      ),
      tags: ["fallback", "determinism"],
    });
  }

  for (const binding of index.bindings) {
    // nullable-identity
    const identity = binding.binding.identity;
    if (identity && expressionIsNullable(identity) && !expressionNarrowsNull(identity)) {
      push({
        rule: "nullable-identity",
        severity: "high",
        title: `Identity of ${binding.kind} "${binding.component}" is not narrowed with drop_null`,
        detail: `Binding ${binding.index} uses a nullable identity expression without drop_null: ${expressionPreview(identity)}.`,
        question: `Binding ${binding.index} targets ${binding.kind} "${binding.component}" with an identity that can be null. Should rows with a missing identity be dropped, or is a null key meaningful?`,
        subject: {
          kind: binding.kind,
          name: binding.component,
          component: binding.component,
          entityKind: binding.kind,
          bindingIndex: binding.index,
        },
        evidence: [
          evidence("binding identity", "blueprint", `${bindingPointer(binding.index)}/identity`),
        ],
        tags: ["identity", "nullability"],
      });
    }

    // shared-nullable-key
    if (binding.kind === "edge") {
      for (const key of ["source_identity", "target_identity"] as const) {
        const endpoint = binding.binding[key];
        if (!endpoint || !expressionIsNullable(endpoint) || expressionNarrowsNull(endpoint)) {
          continue;
        }
        push({
          rule: "shared-nullable-key",
          severity: "medium",
          title: `Edge "${binding.component}" has a nullable ${key.replace("_identity", "")} key`,
          detail: `Binding ${binding.index} ${key.replace("_identity", "")} endpoint is not narrowed with drop_null: ${expressionPreview(endpoint)}.`,
          subject: {
            kind: "edge",
            name: binding.component,
            component: binding.component,
            entityKind: "edge",
            bindingIndex: binding.index,
          },
          evidence: [
            evidence(
              `binding ${key}`,
              "blueprint",
              `${bindingPointer(binding.index)}/${key}`,
            ),
          ],
          tags: ["identity", "edge", "nullability"],
        });
      }
    }
  }

  // multi-source-component and duplicate-target
  const bindingsByComponent = new Map<string, IndexedBinding[]>();
  for (const binding of index.bindings) {
    const key = `${binding.kind}\u0000${binding.component}`;
    const list = bindingsByComponent.get(key) ?? [];
    list.push(binding);
    bindingsByComponent.set(key, list);
  }

  for (const list of bindingsByComponent.values()) {
    if (list.length < 2) continue;
    const signatures = new Map<string, IndexedBinding[]>();
    for (const binding of list) {
      const signature = bindingSignature(binding);
      const group = signatures.get(signature) ?? [];
      group.push(binding);
      signatures.set(signature, group);
    }
    const first = list[0];
    const bindingEvidence = list.map((binding) =>
      evidence(`binding ${binding.index}`, "blueprint", bindingPointer(binding.index)),
    );

    if (signatures.size > 1) {
      const sourceNames = list
        .map((binding) => relationNamesFromRowSource(binding.binding.rows).join("+") || "no relation")
        .join(", ");
      push({
        rule: "multi-source-component",
        severity: "high",
        title: `${first.kind === "node" ? "Node" : "Edge"} "${first.component}" is produced by ${list.length} bindings`,
        detail: `Bindings ${list.map((binding) => binding.index).join(", ")} target the same ${first.kind} from different source branches (${sourceNames}).`,
        question: `${first.kind === "node" ? "Node" : "Edge"} "${first.component}" is produced by ${list.length} bindings from different source branches. Are these intentionally one entity, or should they be separate ${first.kind === "node" ? "node types or entity spaces" : "relationship types"}?`,
        subject: {
          kind: first.kind,
          name: first.component,
          component: first.component,
          entityKind: first.kind,
        },
        evidence: bindingEvidence,
        tags: ["multi-source", "entity-identity"],
      });
    }

    for (const group of signatures.values()) {
      if (group.length < 2) continue;
      push({
        rule: "duplicate-target",
        severity: "high",
        title: `${first.kind === "node" ? "Node" : "Edge"} "${first.component}" has ${group.length} bindings from the same branch`,
        detail: `Bindings ${group.map((binding) => binding.index).join(", ")} produce the same ${first.kind} name from the same source signature and would merge.`,
        question: `${first.kind === "node" ? "Node" : "Edge"} "${first.component}" is produced by ${group.length} bindings from the same source branch. Is one binding redundant, or do they differ in a way the snapshot does not show?`,
        subject: {
          kind: first.kind,
          name: first.component,
          component: first.component,
          entityKind: first.kind,
        },
        evidence: group.map((binding) =>
          evidence(`binding ${binding.index}`, "blueprint", bindingPointer(binding.index)),
        ),
        tags: ["duplicate-target", "cohesion"],
      });
    }
  }

  // -----------------------------------------------------------------------
  // Data and documentation rules
  // -----------------------------------------------------------------------

  const referencedOwners = new Set<string>();
  for (const binding of index.bindings) {
    for (const expression of Object.values(binding.binding.properties ?? {})) {
      for (const fieldRef of collectFieldRefs(expression)) {
        const key = fieldRefKey(fieldRef);
        const owner = key.split(".")[0];
        if (owner) referencedOwners.add(owner);
      }
    }
  }

  (index.blueprint.data?.relations ?? []).forEach((relation, relationIndex) => {
    if (!hasDocumentation(relation)) {
      push({
        rule: "missing-description",
        severity: "low",
        title: `Relation "${relation.name}" has no description or annotation`,
        detail:
          "The relation carries neither a description nor an annotation.",
        subject: { kind: "relation", name: relation.name, component: relation.name },
        evidence: [
          evidence("relation declaration", "blueprint", `/data/relations/${relationIndex}`),
        ],
        tags: ["documentation"],
      });
    }
    if (!referencedOwners.has(relation.name)) {
      push({
        rule: "unused-relation",
        severity: "medium",
        title: `Relation "${relation.name}" is not referenced by any binding field`,
        detail:
          "No binding property expression references a field owned by this relation.",
        subject: { kind: "relation", name: relation.name, component: relation.name },
        evidence: [
          evidence("relation declaration", "blueprint", `/data/relations/${relationIndex}`),
        ],
        tags: ["unused", "data"],
      });
    }
  });

  (index.blueprint.data?.projections ?? []).forEach((projection, projectionIndex) => {
    if (!hasDocumentation(projection)) {
      push({
        rule: "missing-description",
        severity: "low",
        title: `Projection "${projection.name}" has no description or annotation`,
        detail:
          "The projection carries neither a description nor an annotation.",
        subject: {
          kind: "projection",
          name: projection.name,
          component: projection.name,
        },
        evidence: [
          evidence(
            "projection declaration",
            "blueprint",
            `/data/projections/${projectionIndex}`,
          ),
        ],
        tags: ["documentation"],
      });
    }
    if (!referencedOwners.has(projection.name)) {
      push({
        rule: "unused-relation",
        severity: "medium",
        title: `Projection "${projection.name}" is not referenced by any binding field`,
        detail:
          "No binding property expression references a field owned by this projection.",
        subject: {
          kind: "projection",
          name: projection.name,
          component: projection.name,
        },
        evidence: [
          evidence(
            "projection declaration",
            "blueprint",
            `/data/projections/${projectionIndex}`,
          ),
        ],
        tags: ["unused", "data"],
      });
    }
  });

  (index.blueprint.assets ?? []).forEach((asset, assetIndex) => {
    if (!assetHasDocumentation(asset)) {
      push({
        rule: "missing-description",
        severity: "low",
        title: `Asset "${asset.name}" has no description or annotation`,
        detail:
          "The asset carries neither a description, an annotation nor semantic metadata.",
        subject: { kind: "asset", name: asset.name, component: asset.name },
        evidence: [evidence("asset declaration", "blueprint", `/assets/${assetIndex}`)],
        tags: ["documentation"],
      });
    }
    const backsRelation = (index.blueprint.data?.relations ?? []).some(
      (relation) =>
        relation.asset?.[2] === asset.name ||
        resolveAssetName(index, relation.name) === asset.name,
    );
    if (!backsRelation) {
      push({
        rule: "unused-asset",
        severity: "low",
        title: `Asset "${asset.name}" backs no relation`,
        detail:
          "No relation in the snapshot carries this asset as its source, so the asset contributes no data.",
        subject: { kind: "asset", name: asset.name, component: asset.name },
        evidence: [evidence("asset declaration", "blueprint", `/assets/${assetIndex}`)],
        tags: ["unused", "asset"],
      });
    }
  });

  // Topology component documentation.
  (index.blueprint.graph?.nodes ?? []).forEach((node, nodeIndex) => {
    if (hasDocumentation(node)) return;
    push({
      rule: "missing-description",
      severity: "low",
      title: `Node "${node.name}" has no description or annotation`,
      detail: "The topology node carries neither a description nor an annotation.",
      subject: { kind: "node", name: node.name, component: node.name, entityKind: "node" },
      evidence: [evidence("node declaration", "blueprint", `/graph/nodes/${nodeIndex}`)],
      tags: ["documentation"],
    });
  });
  (index.blueprint.graph?.edges ?? []).forEach((edge, edgeIndex) => {
    if (hasDocumentation(edge)) return;
    push({
      rule: "missing-description",
      severity: "low",
      title: `Edge "${edge.name}" has no description or annotation`,
      detail: "The topology edge carries neither a description nor an annotation.",
      subject: { kind: "edge", name: edge.name, component: edge.name, entityKind: "edge" },
      evidence: [evidence("edge declaration", "blueprint", `/graph/edges/${edgeIndex}`)],
      tags: ["documentation"],
    });
  });

  // -----------------------------------------------------------------------
  // Workflow rules
  // -----------------------------------------------------------------------

  index.workflow.steps.forEach((step, indexPosition) => {
    const outgoing = index.outgoingByStepId.get(stepKey(step.id)) ?? [];
    const isTerminal =
      TERMINAL_COMPONENTS.has(step.id[0]) ||
      (step.outputs ?? []).some((output) => TERMINAL_COMPONENTS.has(output.type[0]));

    if (!outgoing.length && !isTerminal) {
      push({
        rule: "orphan-step",
        severity: "low",
        title: `Step "${step.id[0]}/${step.id[1]}" has no consumer`,
        detail:
          "The step output feeds no connection and the step is not a file, meta-graph or Neo4j terminal.",
        subject: stepSubject(step),
        evidence: [
          evidence("workflow step", "workflow", `/steps/${indexPosition}`, step.id),
        ],
        tags: ["workflow", "orphan"],
      });
    }

    (step.outputs ?? []).forEach((output, outputIndex) => {
      const openingName = output.opening_name ?? [];
      const consumed = outgoing.some((connection) =>
        openingMatchesStep(
          connection.output,
          step.id,
          "output",
          openingName,
        ),
      );
      const published = (index.snapshot.report?.published_artifacts ?? []).some(
        (artifact) => {
          if (
            artifact.opening[0] !== step.id[0] ||
            artifact.opening[1] !== step.id[1]
          ) {
            return false;
          }
          if (!openingName.length) return true;
          return openingName.every(
            (value, position) => artifact.opening[3 + position] === value,
          );
        },
      );
      if (consumed || published) return;
      push({
        rule: "unconsumed-output",
        severity: "low",
        title: `Output "${(output.opening_name ?? []).join(".")}" of step "${step.id[0]}/${step.id[1]}" has no consumer`,
        detail:
          "The step output has no workflow connection and is not a published artifact.",
        subject: stepSubject(step),
        evidence: [
          evidence(
            "workflow step output",
            "workflow",
            `/steps/${indexPosition}/outputs/${outputIndex}`,
            output.type,
          ),
        ],
        tags: ["workflow", "unconsumed"],
      });
    });
  });

  // runtime-contract
  (index.workflow.components ?? []).forEach((component, componentIndex) => {
    const runtimeFields = component.runtime_fields ?? [];
    if (!runtimeFields.length) return;
    const descriptions = runtimeFields.map((field) => {
      if (typeof field === "string") return field;
      const record = field as Record<string, unknown>;
      const key = typeof record.key === "string" ? record.key : "runtime field";
      const description =
        typeof record.description === "string" && record.description.trim()
          ? `: ${record.description}`
          : "";
      const valueType =
        typeof record.value_type === "string" ? record.value_type : "unknown type";
      const required = record.required === true ? "required" : "optional";
      return `${key} (${valueType}, ${required})${description}`;
    });
    push({
      rule: "runtime-contract",
      severity: "info",
      title: `Component "${component.id}" declares ${runtimeFields.length} runtime field${runtimeFields.length === 1 ? "" : "s"}`,
      detail: `The environment must supply or may override: ${descriptions.join("; ")}.`,
      subject: {
        kind: "step",
        name: component.id,
        component: component.id,
      },
      evidence: [
        evidence(
          "workflow component",
          "workflow",
          `/components/${componentIndex}`,
        ),
      ],
      tags: ["runtime", "environment"],
    });
  });

  // version-drift (only when provenance records component versions)
  const versionMap = readVersionMap(
    index.snapshot.report?.provenance as Record<string, unknown> | null | undefined,
  );
  if (versionMap) {
    for (const [componentId, recordedVersion] of Object.entries(versionMap)) {
      const component = index.componentsById.get(componentId);
      if (!component?.version) continue;
      if (String(component.version) === String(recordedVersion)) continue;
      push({
        rule: "version-drift",
        severity: "info",
        title: `Component "${componentId}" version differs from the report`,
        detail: `The workflow declares version ${String(component.version)} but the report records ${String(recordedVersion)}.`,
        subject: { kind: "step", name: componentId, component: componentId },
        evidence: [
          evidence("report provenance", "report", "/provenance"),
        ],
        tags: ["version", "provenance"],
      });
    }
  }
  const generatedBy = index.snapshot.metaGraph?.generated_by;
  if (
    generatedBy &&
    typeof generatedBy.module_id === "string" &&
    typeof generatedBy.module_version === "string"
  ) {
    const component = index.componentsById.get(generatedBy.module_id);
    if (component?.version && String(component.version) !== String(generatedBy.module_version)) {
      push({
        rule: "version-drift",
        severity: "info",
        title: `Component "${generatedBy.module_id}" version differs from the meta graph`,
        detail: `The workflow declares version ${String(component.version)} but the meta graph records ${String(generatedBy.module_version)}.`,
        subject: {
          kind: "step",
          name: generatedBy.module_id,
          component: generatedBy.module_id,
        },
        evidence: [evidence("meta graph generator", "metaGraph", "/generated_by")],
        tags: ["version", "provenance"],
      });
    }
  }

  // -----------------------------------------------------------------------
  // Observation rules from the meta graph
  // -----------------------------------------------------------------------

  for (const entry of entries) {
    const metaComponent =
      index.metaGraph.byKey.get(`${entry.kind}\u0000${entry.component}`) ??
      index.metaGraph.byName
        .get(entry.component)
        ?.find((candidate) => candidate.kind === entry.kind);
    if (!metaComponent) continue;
    const metaProperty = metaComponent.properties?.find(
      (candidate) => candidate.name === entry.property.name,
    );
    if (!metaProperty) continue;
    const observedKnown =
      metaProperty.nullable !== undefined ||
      metaProperty.logical_type !== undefined ||
      typeof metaProperty.type === "string";
    if (!observedKnown) continue;
    const declaredNullable = isNullableLogicalType(entry.property.logical_type);
    const observedNullable =
      metaProperty.nullable === true ||
      isNullableLogicalType(metaProperty.logical_type) ||
      (typeof metaProperty.type === "string" && /None/.test(metaProperty.type));
    if (declaredNullable === observedNullable) continue;
    const metaIndex =
      entry.kind === "node"
        ? (index.snapshot.metaGraph?.nodes ?? []).indexOf(metaComponent)
        : (index.snapshot.metaGraph?.edges ?? []).indexOf(metaComponent);
    const metaPropertyIndex =
      metaComponent.properties?.findIndex(
        (candidate) => candidate.name === entry.property.name,
      ) ?? -1;
    push({
      rule: "observe-vs-declare",
      severity: "info",
      title: `Property "${entry.component}.${entry.property.name}" observed nullability differs from its declaration`,
      detail: `The blueprint declares ${declaredNullable ? "a nullable" : "a present"} value; the meta graph observes ${observedNullable ? "nullable" : "present"} values.`,
      subject: {
        kind: "property",
        name: entry.component,
        component: entry.component,
        property: entry.property.name,
        entityKind: entry.kind,
      },
      evidence: [
        evidence(
          "property declaration",
          "blueprint",
          entry.propertyPointer,
          entry.property.ref,
        ),
        evidence(
          "observed property",
          "metaGraph",
          `${entry.kind === "node" ? "/nodes" : "/edges"}/${Math.max(metaIndex, 0)}/properties/${Math.max(metaPropertyIndex, 0)}`,
        ),
      ],
      tags: ["observation", "nullability"],
    });
  }

  // -----------------------------------------------------------------------
  // Build report rules
  // -----------------------------------------------------------------------

  (index.snapshot.report?.unresolved_failures ?? []).forEach((failure, failureIndex) => {
    push({
      rule: "build-failure",
      severity: "critical",
      title: `Unresolved build failure: ${failureText(failure).slice(0, 120)}`,
      detail: failureText(failure),
      ...(failureSubject(failure) ? { subject: failureSubject(failure) } : {}),
      evidence: [
        evidence(
          "unresolved failure",
          "report",
          `/unresolved_failures/${failureIndex}`,
        ),
      ],
      tags: ["build", "failure"],
    });
  });

  (index.snapshot.report?.recovered_failures ?? []).forEach((failure, failureIndex) => {
    push({
      rule: "recovered-failure",
      severity: "high",
      title: `Recovered build failure: ${failureText(failure).slice(0, 120)}`,
      detail: failureText(failure),
      ...(failureSubject(failure) ? { subject: failureSubject(failure) } : {}),
      evidence: [
        evidence(
          "recovered failure",
          "report",
          `/recovered_failures/${failureIndex}`,
        ),
      ],
      tags: ["build", "failure"],
    });
  });

  // -----------------------------------------------------------------------
  // Open sidecar decisions are review questions too
  // -----------------------------------------------------------------------

  for (const decision of review?.decisions ?? []) {
    if (decision.status !== "open") continue;
    const rationale = decision.rationale.trim();
    push({
      rule: "open-decision",
      severity: "medium",
      title: `Open decision: ${decision.title}`,
      detail: rationale || "No rationale was captured for this open decision.",
      question: `The review sidecar records an open decision: "${decision.title}".${rationale ? ` ${rationale}` : " No rationale was captured."} Should this decision be accepted, revised or rejected?`,
      ...(decision.subject ? { subject: decision.subject } : {}),
      evidence: decision.evidence,
      tags: ["decision", "open", ...(decision.tags ?? [])],
    });
  }

  // -----------------------------------------------------------------------
  // Deterministic ordering, counts, questions and rubric
  // -----------------------------------------------------------------------

  const sorted = [...findings.values()].sort((left, right) => {
    const severity = SEVERITY_ORDER[left.severity] - SEVERITY_ORDER[right.severity];
    if (severity) return severity;
    const rule = left.rule.localeCompare(right.rule);
    if (rule) return rule;
    const subject = subjectKey(left.subject).localeCompare(subjectKey(right.subject));
    if (subject) return subject;
    return left.id.localeCompare(right.id);
  });

  const counts = Object.fromEntries(
    SEVERITIES.map((severity) => [severity, 0]),
  ) as Record<Severity, number>;
  for (const finding of sorted) counts[finding.severity] += 1;

  const traceableEntries = entries.filter((entry) => !entry.abstract);
  const totalProperties = traceableEntries.length;
  const tracedProperties = traceableEntries.filter((entry) => {
    const propertyEntries = findComponentPropertyBindings(
      index,
      entry.kind,
      entry.component,
      entry.property.name,
    );
    return propertyEntries.some((candidate) => candidate.fieldRefs.length > 0);
  }).length;

  const documentationSubjects: boolean[] = [
    ...(index.blueprint.graph?.nodes ?? []).map((node) => hasDocumentation(node)),
    ...(index.blueprint.graph?.edges ?? []).map((edge) => hasDocumentation(edge)),
    ...entries.map((entry) => hasDocumentation(entry.property)),
    ...(index.blueprint.data?.relations ?? []).map((relation) => hasDocumentation(relation)),
    ...(index.blueprint.data?.projections ?? []).map((projection) =>
      hasDocumentation(projection),
    ),
    ...(index.blueprint.assets ?? []).map((asset) => assetHasDocumentation(asset)),
  ];
  const documentedSubjects = documentationSubjects.filter(Boolean).length;

  let expressionsTotal = 0;
  let riskyExpressions = 0;
  for (const binding of index.bindings) {
    for (const expression of Object.values(binding.binding.properties ?? {})) {
      expressionsTotal += 1;
      const literalOnly = collectFieldRefs(expression).length === 0;
      const fallback = fallbackLiterals(expression).length > 0;
      if (literalOnly || fallback) riskyExpressions += 1;
    }
  }

  const unresolvedFailures = index.snapshot.report?.unresolved_failures?.length ?? 0;
  const recoveredFailures = index.snapshot.report?.recovered_failures?.length ?? 0;
  const compileOnly =
    Boolean(index.snapshot.report?.provenance) &&
    typeof index.snapshot.report.provenance === "object" &&
    (index.snapshot.report.provenance as Record<string, unknown>).mode ===
      "compile-only";
  const multiSourceCount = sorted.filter(
    (finding) => finding.rule === "multi-source-component",
  ).length;
  const duplicateTargetCount = sorted.filter(
    (finding) => finding.rule === "duplicate-target",
  ).length;

  const components: AuditScoreComponent[] = [
    {
      id: "traceability",
      label: "Traceability",
      value: rounded(percentage(tracedProperties, totalProperties)),
      weight: 0.25,
      detail: `${tracedProperties} of ${totalProperties} topology properties reference at least one field.`,
    },
    {
      id: "documentation",
      label: "Documentation",
      value: rounded(percentage(documentedSubjects, documentationSubjects.length)),
      weight: 0.2,
      detail: `${documentedSubjects} of ${documentationSubjects.length} subjects carry a description or annotation.`,
    },
    {
      id: "determinism",
      label: "Determinism",
      value: rounded(percentage(expressionsTotal - riskyExpressions, expressionsTotal)),
      weight: 0.2,
      detail: `${expressionsTotal - riskyExpressions} of ${expressionsTotal} property expressions avoid literal-only or fallback values.`,
    },
    {
      id: "verification",
      label: "Verification",
      value: compileOnly
        ? 0
        : rounded(
            Math.max(0, 100 - unresolvedFailures * 40 - recoveredFailures * 10),
          ),
      weight: 0.2,
      detail: compileOnly
        ? "Compile-only snapshot: the graph was not executed, so execution verification did not run."
        : `${unresolvedFailures} unresolved and ${recoveredFailures} recovered failures in the build report.`,
    },
    {
      id: "cohesion",
      label: "Cohesion",
      value: rounded(
        Math.max(0, 100 - multiSourceCount * 12 - duplicateTargetCount * 18),
      ),
      weight: 0.15,
      detail: `${multiSourceCount} multi-source components and ${duplicateTargetCount} duplicate targets.`,
    },
  ];

  const weighted = components.reduce(
    (total, component) => total + component.value * component.weight,
    0,
  );

  return {
    findings: sorted,
    counts,
    score: {
      value: Math.max(0, Math.min(100, Math.round(weighted))),
      components,
    },
    questions: sorted.filter((finding) => Boolean(finding.question)),
  };
}
