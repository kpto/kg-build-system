/**
 * Deterministic audit engine.
 *
 * A finding is one statement about the loaded snapshot with at least one
 * artifact pointer. The engine never executes a build, never reads a clock and
 * never calls a model. It reports identity, grounding, type/presence and
 * semantics-presence defects; it deliberately has no rubric or health score.
 *
 * Finding identities are stable: `rule + subject + evidence pointers` hashed
 * with FNV-1a. Reordering the snapshot does not renumber a finding that still
 * refers to the same artifacts.
 */

import type {
  EntityKind,
  Expression,
  IndexedBinding,
  LogicalType,
  Ref,
  SemanticSubject,
  SemanticsDTO,
  TopologyEdge,
  TopologyNode,
  TopologyProperty,
  ViewerIndex,
  WorkflowStep,
} from "./types";
import type {
  AuditFinding,
  AuditReport,
  AuditSubject,
  EvidenceRef,
  ReviewSidecar,
  Severity,
} from "./reviewTypes";
import {
  findComponentPropertyBindings,
  relationNamesFromRowSource,
} from "./indexes";
import { collectFieldRefs, expressionPreview, fieldRefKey, walkExpression } from "./expressions";

export type AuditRuleGroupId =
  | "identity"
  | "coverage"
  | "semantics"
  | "type"
  | "graph";

export const AUDIT_RULE_GROUPS: ReadonlyArray<{
  id: AuditRuleGroupId;
  label: string;
  detail: string;
}> = [
  {
    id: "identity",
    label: "Identity",
    detail: "Keys, endpoints, producers and inherited component contracts.",
  },
  {
    id: "coverage",
    label: "Grounding",
    detail: "Properties and bindings that do not reach a source.",
  },
  {
    id: "semantics",
    label: "Semantics",
    detail: "Declarations without an attached semantic unit.",
  },
  {
    id: "type",
    label: "Type & presence",
    detail: "Lossy narrowing and incompatible logical-type shapes.",
  },
  {
    id: "graph",
    label: "Graph",
    detail: "The graph declaration and its purpose.",
  },
];

/** The group a rule belongs to; the rule id names its group as a prefix. */
export function auditRuleGroup(rule: string): AuditRuleGroupId {
  const prefix = rule.split(".")[0];
  return (AUDIT_RULE_GROUPS.find((group) => group.id === prefix)?.id ?? "identity") as AuditRuleGroupId;
}

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low", "info"];

const FALLBACK_OPERATORS = new Set(["coalesce", "default_to"]);

const MAX_UPSTREAM_HOPS = 64;

type PropertyEntry = {
  kind: EntityKind;
  component: string;
  property: TopologyProperty;
  componentPointer: string;
  propertyPointer: string;
  abstract: boolean;
};

// ---------------------------------------------------------------------------
// Deterministic identity helpers
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Types, expressions and semantics
// ---------------------------------------------------------------------------

function hasSemanticUnits(semantics: SemanticsDTO | undefined): boolean {
  return Boolean(
    semantics &&
      ((semantics.claims?.length ?? 0) > 0 || (semantics.frames?.length ?? 0) > 0),
  );
}

function isNullableLogicalType(value: unknown): boolean {
  if (!value || typeof value !== "object") return false;
  return (value as { kind?: unknown }).kind === "nullable";
}

function unwrapNullable(value: LogicalType | undefined): LogicalType | undefined {
  let current = value;
  const seen = new Set<LogicalType>();
  while (current && current.kind === "nullable" && current.value && !seen.has(current)) {
    seen.add(current);
    current = current.value;
  }
  return current;
}

function expressionIsNullable(expression: Expression | undefined): boolean {
  return Boolean(expression && isNullableLogicalType(expression.logical_type));
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

function fallbackOperators(expression: Expression | undefined): string[] {
  const operators = new Set<string>();
  walkExpression(expression, (node) => {
    if (node.kind !== "operation") return;
    const name = node.operator.at(-1) ?? "";
    if (FALLBACK_OPERATORS.has(name)) operators.add(name);
  });
  return [...operators].sort();
}

/**
 * A key is a fallback when it uses `default_to`/`coalesce`, when it is a
 * literal, or when it is a constant-only expression. A legitimate namespace
 * literal inside a `concat` that still references a field is not a fallback.
 */
function keyUsesFallback(expression: Expression | undefined): {
  operators: string[];
  literalOnly: boolean;
} {
  if (!expression) return { operators: [], literalOnly: false };
  const operators = fallbackOperators(expression);
  const literals = collectLiteralValues(expression);
  const fields = collectFieldRefs(expression);
  const literalOnly =
    literals.length > 0 && fields.length === 0 && expression.kind !== "field";
  const fallbackWithLiteral =
    operators.length > 0 &&
    walkExpressionHasLiteralInsideFallback(expression);
  return {
    operators,
    literalOnly: literalOnly || fallbackWithLiteral,
  };
}

function collectLiteralValues(expression: Expression | undefined): unknown[] {
  const values: unknown[] = [];
  walkExpression(expression, (node) => {
    if (node.kind === "literal") values.push(node.value);
  });
  return values;
}

function walkExpressionHasLiteralInsideFallback(expression: Expression): boolean {
  let found = false;
  const visit = (node: Expression) => {
    if (found) return;
    if (node.kind !== "operation") return;
    const name = node.operator.at(-1) ?? "";
    if (
      FALLBACK_OPERATORS.has(name) &&
      (node.arguments ?? []).some((argument) => argument.kind === "literal")
    ) {
      found = true;
      return;
    }
    for (const argument of node.arguments ?? []) visit(argument);
  };
  visit(expression);
  return found;
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

function describeType(type: LogicalType | undefined): string {
  if (!type) return "unknown";
  if (type.kind === "nullable") return `${describeType(type.value)} | None`;
  if (type.kind === "unit") return type.name ? `unit<${type.name}>` : "unit";
  if (type.kind === "array") return `array<${describeType(type.item)}>`;
  if (type.kind === "struct") return type.name ? `struct<${type.name}>` : "struct";
  return type.name ? `${type.kind}<${type.name}>` : type.kind;
}

function isAssignableType(
  source: LogicalType | undefined,
  target: LogicalType | undefined,
  seen: Set<string> = new Set(),
): boolean {
  const from = unwrapNullable(source);
  const to = unwrapNullable(target);
  if (!from || !to) return true;
  if (to.kind === "any" || to.kind === "unknown") return true;
  if (from.kind === "any" || from.kind === "unknown") return true;
  if (from.kind !== to.kind) return false;

  const key = `${stableStringify(from)}->${stableStringify(to)}`;
  if (seen.has(key)) return true;
  seen.add(key);

  if (from.kind === "unit") {
    if (from.name && to.name && from.name !== to.name) return false;
    return true;
  }
  if (from.kind === "array") {
    if (!from.item || !to.item) return true;
    return isAssignableType(from.item, to.item, seen);
  }
  if (from.kind === "struct") {
    if (from.qualname && to.qualname && from.qualname !== to.qualname) return false;
    if (from.name && to.name && from.name !== to.name) return false;
    return true;
  }
  return true;
}

function expressionLogicalType(
  index: ViewerIndex,
  expression: Expression | undefined,
): LogicalType | undefined {
  if (!expression) return undefined;
  if (expression.logical_type) return expression.logical_type;
  for (const fieldRef of collectFieldRefs(expression)) {
    const location = index.fieldsByKey.get(fieldRefKey(fieldRef));
    if (location?.field.logical_type) return location.field.logical_type;
  }
  return undefined;
}

// ---------------------------------------------------------------------------
// Topology and workflow helpers
// ---------------------------------------------------------------------------

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

function componentPointer(index: ViewerIndex, kind: EntityKind, name: string): string {
  const list = kind === "node" ? index.blueprint.graph?.nodes : index.blueprint.graph?.edges;
  const position = (list ?? []).findIndex((component) => component.name === name);
  return `${kind === "node" ? "/graph/nodes" : "/graph/edges"}/${Math.max(position, 0)}`;
}

function propertyPointer(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
  property: string,
): string {
  const list = kind === "node" ? index.blueprint.graph?.nodes : index.blueprint.graph?.edges;
  const componentIndex = (list ?? []).findIndex((entry) => entry.name === component);
  const componentEntry = componentIndex >= 0 ? list?.[componentIndex] : undefined;
  const propertyIndex = componentEntry?.properties?.findIndex(
    (entry) => entry.name === property,
  ) ?? -1;
  return `${kind === "node" ? "/graph/nodes" : "/graph/edges"}/${Math.max(
    componentIndex,
    0,
  )}/properties/${Math.max(propertyIndex, 0)}`;
}

function bindingPointer(index: number): string {
  return `/bindings/${index}`;
}

function bindingPropertyPointer(index: number, property: string): string {
  return `/bindings/${index}/properties/${pointerSegment(property)}`;
}

function componentBindings(
  index: ViewerIndex,
  kind: EntityKind,
  component: string,
): IndexedBinding[] {
  return index.bindings.filter(
    (binding) => binding.kind === kind && binding.component === component,
  );
}

function bindingHasProperty(binding: IndexedBinding, property: string): boolean {
  return Object.prototype.hasOwnProperty.call(
    binding.binding.properties ?? {},
    property,
  );
}

function componentObject(
  index: ViewerIndex,
  kind: EntityKind,
  name: string,
): TopologyNode | TopologyEdge | undefined {
  return kind === "node"
    ? index.topologyNodesByName.get(name)
    : index.topologyEdgesByName.get(name);
}

function parentName(component: TopologyNode | TopologyEdge | undefined): string | undefined {
  return component?.parent?.[2];
}

/** Ancestor components, nearest first, with cycle protection. */
function ancestorsOf(
  index: ViewerIndex,
  kind: EntityKind,
  component: TopologyNode | TopologyEdge | undefined,
): Array<TopologyNode | TopologyEdge> {
  const result: Array<TopologyNode | TopologyEdge> = [];
  const seen = new Set<string>();
  let parent = parentName(component);
  while (parent && !seen.has(parent)) {
    seen.add(parent);
    const ancestor = componentObject(index, kind, parent);
    if (!ancestor) break;
    result.push(ancestor);
    parent = parentName(ancestor);
  }
  return result;
}

function isConcreteDescendant(
  index: ViewerIndex,
  kind: EntityKind,
  name: string,
  abstractName: string,
): boolean {
  const component = componentObject(index, kind, name);
  if (!component || component.abstract === true) return false;
  return ancestorsOf(index, kind, component).some(
    (ancestor) => ancestor.name === abstractName,
  );
}

function hasUpstreamSourceStep(index: ViewerIndex, start: WorkflowStep | undefined): boolean {
  if (!start) return false;
  const queue: Array<{ step: WorkflowStep; hops: number }> = [{ step: start, hops: 0 }];
  const visited = new Set<string>([`${start.id[0]}\u0000${start.id[1]}`]);
  while (queue.length) {
    const current = queue.shift();
    if (!current || current.hops > MAX_UPSTREAM_HOPS) continue;
    const step = current.step;
    if (
      (step.outputs ?? []).some(
        (output) =>
          output.type[2] === "table" ||
          output.type[1] === "source" ||
          output.type[0] === "source",
      ) ||
      step.instruction.kind[0] === "source_relation"
    ) {
      return true;
    }
    const key = `${step.id[0]}\u0000${step.id[1]}`;
    for (const connection of index.incomingByStepId.get(key) ?? []) {
      const upstream = index.stepsById.get(
        `${connection.outputStepId[0]}\u0000${connection.outputStepId[1]}`,
      );
      if (!upstream) continue;
      const upstreamKey = `${upstream.id[0]}\u0000${upstream.id[1]}`;
      if (visited.has(upstreamKey)) continue;
      visited.add(upstreamKey);
      queue.push({ step: upstream, hops: current.hops + 1 });
    }
  }
  return false;
}

function allBindingExpressions(binding: IndexedBinding): Expression[] {
  return [
    binding.binding.identity,
    binding.binding.source_identity,
    binding.binding.target_identity,
    ...Object.values(binding.binding.properties ?? {}),
  ].filter((expression): expression is Expression => Boolean(expression));
}

function sourceRelations(binding: IndexedBinding): string[] {
  return relationNamesFromRowSource(binding.binding.rows).sort();
}

// ---------------------------------------------------------------------------
// Semantic subject pointers
// ---------------------------------------------------------------------------

function semanticPointer(index: ViewerIndex, subject: SemanticSubject): string {
  switch (subject.kind) {
    case "graph":
      return "/graph_declaration";
    case "asset":
      return `/assets/${Math.max(index.assets.findIndex((asset) => asset.name === subject.name), 0)}`;
    case "relation":
      return `/data/relations/${Math.max(
        (index.blueprint.data?.relations ?? []).findIndex(
          (relation) => relation.name === subject.name,
        ),
        0,
      )}`;
    case "projection":
      return `/data/projections/${Math.max(
        (index.blueprint.data?.projections ?? []).findIndex(
          (projection) => projection.name === subject.name,
        ),
        0,
      )}`;
    case "struct":
      return `/data/structs/${Math.max(
        (index.blueprint.data?.structs ?? []).findIndex(
          (struct) => struct.name === subject.name,
        ),
        0,
      )}`;
    case "field": {
      const [, ownerKind, ownerName] = subject.key.split("\u0000");
      const collection =
        ownerKind === "projection"
          ? index.blueprint.data?.projections
          : ownerKind === "struct"
            ? index.blueprint.data?.structs
            : index.blueprint.data?.relations;
      const base =
        ownerKind === "projection"
          ? "/data/projections"
          : ownerKind === "struct"
            ? "/data/structs"
            : "/data/relations";
      const ownerIndex = (collection ?? []).findIndex((owner) => owner.name === ownerName);
      const owner = ownerIndex >= 0 ? collection?.[ownerIndex] : undefined;
      const fieldIndex = owner?.columns?.findIndex((field) => field.name === subject.name) ?? -1;
      return `${base}/${Math.max(ownerIndex, 0)}/columns/${Math.max(fieldIndex, 0)}`;
    }
    case "node":
    case "edge":
      return componentPointer(index, subject.kind, subject.name);
    case "property": {
      const [, entityKind, component, property] = subject.key.split("\u0000");
      return propertyPointer(
        index,
        entityKind === "edge" ? "edge" : "node",
        component,
        property,
      );
    }
    case "binding":
      return bindingPointer(subject.bindingIndex ?? 0);
  }
}

function semanticSubjectForFinding(subject: SemanticSubject): AuditSubject {
  switch (subject.kind) {
    case "graph":
    case "struct":
      return {
        kind: subject.kind as AuditSubject["kind"],
        name: subject.name,
        component: subject.name,
      };
    case "field":
      return {
        kind: subject.kind as AuditSubject["kind"],
        name: subject.name,
        component: subject.ownerName ?? subject.name,
      };
    case "property":
      return {
        kind: "property",
        name: subject.ownerName ?? subject.name,
        component: subject.ownerName ?? subject.name,
        property: subject.name,
        ...(subject.entityKind ? { entityKind: subject.entityKind } : {}),
      };
    case "binding":
      return {
        kind: "binding",
        name: subject.name,
        component: subject.ref?.[2] ?? subject.name,
        ...(subject.entityKind ? { entityKind: subject.entityKind } : {}),
        ...(subject.bindingIndex !== undefined
          ? { bindingIndex: subject.bindingIndex }
          : {}),
      };
    case "node":
    case "edge":
      return {
        kind: subject.kind,
        name: subject.name,
        component: subject.name,
        entityKind: subject.kind,
      };
    case "asset":
    case "relation":
    case "projection":
      return {
        kind: subject.kind,
        name: subject.name,
        component: subject.name,
      };
  }
}

function semanticSeverity(kind: SemanticSubject["kind"]): Severity {
  return kind === "field" || kind === "property" || kind === "binding"
    ? "low"
    : "medium";
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------

/**
 * Build the deterministic audit report for a loaded snapshot.
 *
 * `review` is accepted for the ledger contract. Decisions are review state, not
 * snapshot facts, so they never become audit findings; the view reads the same
 * sidecar to show a decision status beside a finding.
 */
export function buildAudit(index: ViewerIndex, review?: ReviewSidecar): AuditReport {
  void review;
  const findings = new Map<string, AuditFinding>();
  const push = (draft: Omit<AuditFinding, "id">): void => {
    const id = stableFindingId(draft.rule, draft.subject, draft.evidence);
    if (!findings.has(id)) findings.set(id, { ...draft, id });
  };

  const entries = topologyEntries(index);

  // -----------------------------------------------------------------------
  // graph.purpose-missing
  // -----------------------------------------------------------------------

  const declaration = index.graphDeclaration;
  if (!declaration || !nonEmpty(declaration.semantics?.purpose?.text)) {
    const subject: AuditSubject = {
      kind: "graph" as AuditSubject["kind"],
      name: declaration?.name ?? index.snapshot.name,
      component: declaration?.name ?? index.snapshot.name,
    };
    push({
      rule: "graph.purpose-missing",
      severity: "critical",
      title: declaration
        ? `Graph "${declaration.name}" has no purpose`
        : "Snapshot has no graph declaration",
      detail: declaration
        ? "The graph declaration carries an empty or missing purpose. A consumer cannot tell what the graph is for."
        : "The blueprint has no graph declaration, so the graph has no stated purpose.",
      question: "What is this graph for, and which declaration states that purpose?",
      subject,
      evidence: [
        evidence(
          declaration ? "graph declaration" : "graph declaration (absent)",
          "blueprint",
          "/graph_declaration",
        ),
      ],
      tags: ["graph", "purpose", "semantics"],
    });
  }

  // -----------------------------------------------------------------------
  // Identity rules
  // -----------------------------------------------------------------------

  for (const binding of index.bindings) {
    const subject: AuditSubject = {
      kind: binding.kind,
      name: binding.component,
      component: binding.component,
      entityKind: binding.kind,
      bindingIndex: binding.index,
    };
    const identity = binding.binding.identity;
    const identityEvidence = [
      evidence("binding identity", "blueprint", `${bindingPointer(binding.index)}/identity`),
    ];

    const keyRoles = (
      [
        ["identity", binding.binding.identity],
        ["source_identity", binding.binding.source_identity],
        ["target_identity", binding.binding.target_identity],
      ] as const
    ).filter(([, expression]) => Boolean(expression));

    const fallbackRoles: Array<{
      role: string;
      mechanism: string;
      expression: Expression;
    }> = [];
    for (const [role, expression] of keyRoles) {
      if (!expression) continue;
      const fallback = keyUsesFallback(expression);
      if (!fallback.operators.length && !fallback.literalOnly) continue;
      const mechanism = [
        ...fallback.operators,
        ...(fallback.literalOnly && !fallback.operators.length ? ["literal key"] : []),
      ].join(", ");
      fallbackRoles.push({ role, mechanism, expression });
    }
    if (fallbackRoles.length) {
      const roles = fallbackRoles.map((entry) => entry.role).join(", ");
      const mechanisms = [...new Set(fallbackRoles.map((entry) => entry.mechanism))].join(", ");
      push({
        rule: "identity.key-fallback",
        severity: "high",
        title: `Identity of ${binding.kind} "${binding.component}" falls back to a constant`,
        detail: `Binding ${binding.index} builds ${roles} with ${mechanisms}: ${fallbackRoles
          .map((entry) => `${entry.role} = ${expressionPreview(entry.expression)}`)
          .join("; ")}. A fallback constant lets distinct source rows share one identity.`,
        question: `The ${binding.kind} "${binding.component}" key uses ${mechanisms}. Is a fallback identity intended, or should a row without a real key be rejected?`,
        subject,
        evidence: fallbackRoles.map((entry) =>
          evidence(
            `binding ${entry.role}`,
            "blueprint",
            `${bindingPointer(binding.index)}/${entry.role}`,
          ),
        ),
        tags: ["identity", "fallback", "determinism"],
      });
    }

    if (identity) {
      if (expressionIsNullable(identity) && !expressionNarrowsNull(identity)) {
        push({
          rule: "identity.nullable-key",
          severity: "high",
          title: `Identity of ${binding.kind} "${binding.component}" is nullable`,
          detail: `Binding ${binding.index} uses a nullable identity without drop_null: ${expressionPreview(identity)}.`,
          question: `The ${binding.kind} "${binding.component}" identity can be null. Should rows with a missing identity be dropped?`,
          subject,
          evidence: identityEvidence,
          tags: ["identity", "nullability"],
        });
      }
    }

    if (binding.kind === "edge") {
      const missing: string[] = [];
      const endpointEvidence: EvidenceRef[] = [];
      for (const role of ["source_identity", "target_identity"] as const) {
        const endpoint = binding.binding[role];
        const endpointName = role.replace("_identity", "");
        if (!endpoint) {
          missing.push(endpointName);
          endpointEvidence.push(
            evidence(`binding ${role} (absent)`, "blueprint", `${bindingPointer(binding.index)}/${role}`),
          );
          continue;
        }
        endpointEvidence.push(
          evidence(`binding ${role}`, "blueprint", `${bindingPointer(binding.index)}/${role}`),
        );
        if (expressionIsNullable(endpoint) && !expressionNarrowsNull(endpoint)) {
          push({
            rule: "identity.edge-endpoint-nullable",
            severity: "high",
            title: `Edge "${binding.component}" has a nullable ${endpointName} identity`,
            detail: `Binding ${binding.index} ${endpointName} identity is nullable and is not narrowed: ${expressionPreview(endpoint)}.`,
            question: `The ${endpointName} endpoint of edge "${binding.component}" can be null. Should the relationship be dropped when either endpoint is absent?`,
            subject: { ...subject, name: `${binding.component}.${endpointName}` },
            evidence: [
              evidence(
                `binding ${role}`,
                "blueprint",
                `${bindingPointer(binding.index)}/${role}`,
              ),
            ],
            tags: ["identity", "edge", "nullability"],
          });
        }
      }
      if (missing.length) {
        push({
          rule: "identity.missing-endpoint",
          severity: "high",
          title: `Edge "${binding.component}" has no ${missing.join(" or ")} identity`,
          detail: `Binding ${binding.index} does not declare ${missing.join(" and ")} identity for the edge, so the relationship endpoint cannot be resolved.`,
          question: `Edge "${binding.component}" is missing ${missing.join(" and ")} identity. Which fields identify its endpoints?`,
          subject,
          evidence: endpointEvidence,
          tags: ["identity", "edge", "endpoint"],
        });
      }
    }
  }

  // Unbound concrete components.
  const components = [...(index.blueprint.graph?.nodes ?? []), ...(index.blueprint.graph?.edges ?? [])];
  for (const component of components) {
    if (component.abstract === true) continue;
    const kind: EntityKind = index.topologyNodesByName.has(component.name) &&
      index.topologyNodesByName.get(component.name) === component
      ? "node"
      : "edge";
    const bindings = componentBindings(index, kind, component.name);
    if (bindings.length) continue;
    push({
      rule: "identity.unbound-component",
      severity: "high",
      title: `Concrete ${kind} "${component.name}" has no binding`,
      detail: `No blueprint binding produces the concrete ${kind} "${component.name}", so it has no rows or identity.`,
      question: `Concrete ${kind} "${component.name}" has no binding. Is it intentionally unpopulated, or was its producer omitted?`,
      subject: {
        kind,
        name: component.name,
        component: component.name,
        entityKind: kind,
      },
      evidence: [
        evidence(`${kind} declaration`, "blueprint", componentPointer(index, kind, component.name)),
      ],
      tags: ["identity", "binding", "coverage"],
    });
  }

  // Abstract categories without a concrete producer.
  for (const component of components) {
    if (component.abstract !== true) continue;
    const kind: EntityKind =
      index.topologyNodesByName.get(component.name) === component ? "node" : "edge";
    const ownBinding = componentBindings(index, kind, component.name).length > 0;
    const descendant = components.some(
      (candidate) =>
        candidate !== component &&
        isConcreteDescendant(index, kind, candidate.name, component.name),
    );
    if (ownBinding || descendant) continue;
    push({
      rule: "identity.abstract-no-producer",
      severity: "medium",
      title: `Abstract ${kind} "${component.name}" has no concrete producer`,
      detail: `The abstract category "${component.name}" declares no binding and no concrete ${kind} descends from it.`,
      question: `Abstract ${kind} "${component.name}" has no concrete child or binding. Is the category intentionally empty?`,
      subject: {
        kind,
        name: component.name,
        component: component.name,
        entityKind: kind,
      },
      evidence: [
        evidence(`${kind} declaration`, "blueprint", componentPointer(index, kind, component.name)),
      ],
      tags: ["identity", "abstract", "coverage"],
    });
  }

  // Inherited properties on concrete components.
  for (const component of components) {
    if (component.abstract === true) continue;
    const kind: EntityKind =
      index.topologyNodesByName.get(component.name) === component ? "node" : "edge";
    const bindings = componentBindings(index, kind, component.name);
    const localProperties = new Set((component.properties ?? []).map((property) => property.name));
    const seen = new Set<string>();
    for (const ancestor of ancestorsOf(index, kind, component)) {
      for (const property of ancestor.properties ?? []) {
        if (localProperties.has(property.name) || seen.has(property.name)) continue;
        seen.add(property.name);
        if (bindings.some((binding) => bindingHasProperty(binding, property.name))) continue;
        push({
          rule: "identity.inherited-property-missing",
          severity: "high",
          title: `Concrete ${kind} "${component.name}" does not bind inherited property "${property.name}"`,
          detail: `Property "${property.name}" is inherited from abstract ${kind} "${ancestor.name}", but no binding for "${component.name}" declares it.`,
          question: `The ${kind} "${component.name}" inherits "${property.name}" from "${ancestor.name}". Which source expression supplies it?`,
          subject: {
            kind: "property",
            name: component.name,
            component: component.name,
            property: property.name,
            entityKind: kind,
          },
          evidence: [
            evidence(
              "concrete declaration",
              "blueprint",
              componentPointer(index, kind, component.name),
            ),
            evidence(
              "inherited property",
              "blueprint",
              propertyPointer(index, kind, ancestor.name, property.name),
            ),
            ...bindings.map((binding) =>
              evidence(`binding ${binding.index}`, "blueprint", bindingPointer(binding.index)),
            ),
          ],
          tags: ["identity", "inheritance", "property"],
        });
      }
    }
  }

  // Duplicate and multi-source producers.
  const bindingsByComponent = new Map<string, IndexedBinding[]>();
  for (const binding of index.bindings) {
    const key = `${binding.kind}\u0000${binding.component}`;
    const list = bindingsByComponent.get(key) ?? [];
    list.push(binding);
    bindingsByComponent.set(key, list);
  }

  for (const list of bindingsByComponent.values()) {
    if (list.length < 2) continue;
    const first = list[0];
    const signatures = new Map<string, IndexedBinding[]>();
    for (const binding of list) {
      const signature = stableStringify(binding.binding.rows ?? null);
      const group = signatures.get(signature) ?? [];
      group.push(binding);
      signatures.set(signature, group);
    }
    const subject: AuditSubject = {
      kind: first.kind,
      name: first.component,
      component: first.component,
      entityKind: first.kind,
    };
    const bindingEvidence = list.map((binding) =>
      evidence(`binding ${binding.index}`, "blueprint", bindingPointer(binding.index)),
    );

    if (signatures.size > 1) {
      const relations = list.map((binding) => sourceRelations(binding).join("+") || "no relation");
      const severity: Severity = new Set(relations).size > 1 ? "high" : "medium";
      push({
        rule: "identity.multi-source-component",
        severity,
        title: `${first.kind === "node" ? "Node" : "Edge"} "${first.component}" is produced by ${list.length} source branches`,
        detail: `Bindings ${list.map((binding) => binding.index).join(", ")} target the same ${first.kind} from different branches (${relations.join(", ")}).`,
        question: `The ${first.kind} "${first.component}" is produced from multiple source branches. Are these intentionally one entity, or should they be separate ${first.kind} types?`,
        subject,
        evidence: bindingEvidence,
        tags: ["identity", "multi-source", "cohesion"],
      });
    }

    for (const group of signatures.values()) {
      if (group.length < 2) continue;
      push({
        rule: "identity.duplicate-producer",
        severity: "high",
        title: `${first.kind === "node" ? "Node" : "Edge"} "${first.component}" has ${group.length} bindings from the same branch`,
        detail: `Bindings ${group.map((binding) => binding.index).join(", ")} produce the same ${first.kind} from the same source branch and would merge.`,
        question: `The ${first.kind} "${first.component}" has ${group.length} bindings from one branch. Is one binding redundant, or do they differ in a way the snapshot does not show?`,
        subject,
        evidence: group.map((binding) =>
          evidence(`binding ${binding.index}`, "blueprint", bindingPointer(binding.index)),
        ),
        tags: ["identity", "duplicate", "producer"],
      });
    }
  }

  // -----------------------------------------------------------------------
  // Coverage rules
  // -----------------------------------------------------------------------

  for (const entry of entries) {
    if (entry.abstract) continue;
    const propertyEntries = findComponentPropertyBindings(
      index,
      entry.kind,
      entry.component,
      entry.property.name,
    );
    const boundEntries = propertyEntries.filter((candidate) =>
      Boolean(candidate.expression),
    );
    const expressions = boundEntries
      .map((candidate) => candidate.expression)
      .filter((expression): expression is Expression => Boolean(expression));

    if (!boundEntries.length) {
      push({
        rule: "coverage.unbound-property",
        severity: "high",
        title: `Property "${entry.component}.${entry.property.name}" has no binding`,
        detail: "No blueprint binding declares an expression for this topology property, so its lineage cannot be resolved.",
        question: `Property "${entry.component}.${entry.property.name}" has no binding. Is it intentionally unbound, or was its binding omitted?`,
        subject: {
          kind: "property",
          name: entry.component,
          component: entry.component,
          property: entry.property.name,
          entityKind: entry.kind,
        },
        evidence: [
          evidence("property declaration", "blueprint", entry.propertyPointer, entry.property.ref),
        ],
        tags: ["coverage", "lineage", "property"],
      });
      continue;
    }

    if (
      expressions.length > 0 &&
      expressions.every((expression) => collectFieldRefs(expression).length === 0)
    ) {
      push({
        rule: "coverage.literal-only",
        severity: "medium",
        title: `Property "${entry.component}.${entry.property.name}" is defined only by literals`,
        detail: `The property has no field reference to a source relation: ${expressions
          .map((expression) => expressionPreview(expression))
          .join(", ")}.`,
        question: `Property "${entry.component}.${entry.property.name}" is a literal. Is this a constant the graph owns, or should it be read from a source?`,
        subject: {
          kind: "property",
          name: entry.component,
          component: entry.component,
          property: entry.property.name,
          entityKind: entry.kind,
          ...(boundEntries[0] ? { bindingIndex: boundEntries[0].binding.index } : {}),
        },
        evidence: [
          evidence("property declaration", "blueprint", entry.propertyPointer, entry.property.ref),
          ...boundEntries.map((candidate) =>
            evidence(
              `binding ${candidate.binding.index} property expression`,
              "blueprint",
              bindingPropertyPointer(candidate.binding.index, entry.property.name),
            ),
          ),
        ],
        tags: ["coverage", "literal", "traceability"],
      });
    }

    // Type and presence rules share the same property expression evidence.
    for (const candidate of boundEntries) {
      const expression = candidate.expression;
      if (!expression) continue;
      const bindingSubject: AuditSubject = {
        kind: "property",
        name: entry.component,
        component: entry.component,
        property: entry.property.name,
        entityKind: entry.kind,
        bindingIndex: candidate.binding.index,
      };
      const expressionPointer = bindingPropertyPointer(
        candidate.binding.index,
        entry.property.name,
      );
      const declaredNullable = isNullableLogicalType(entry.property.logical_type);

      if (
        expressionIsNullable(expression) &&
        !declaredNullable &&
        !expressionNarrowsNull(expression)
      ) {
        push({
          rule: "type.presence-mismatch",
          severity: "high",
          title: `Property "${entry.component}.${entry.property.name}" receives a nullable value`,
          detail: `The property declares ${describeType(entry.property.logical_type)}, but binding ${candidate.binding.index} supplies a nullable ${describeType(
            expression.logical_type,
          )} without narrowing: ${expressionPreview(expression)}.`,
          question: `Property "${entry.component}.${entry.property.name}" is required but its expression can be null. Should the binding drop or coalesce nulls?`,
          subject: bindingSubject,
          evidence: [
            evidence("property declaration", "blueprint", entry.propertyPointer, entry.property.ref),
            evidence("binding property expression", "blueprint", expressionPointer),
          ],
          tags: ["type", "presence", "nullability"],
        });
      }

      const sourceType = expressionLogicalType(index, expression);
      if (!isAssignableType(sourceType, entry.property.logical_type)) {
        push({
          rule: "type.shape-mismatch",
          severity: "high",
          title: `Property "${entry.component}.${entry.property.name}" expects ${describeType(
            entry.property.logical_type,
          )} but receives ${describeType(sourceType)}`,
          detail: `Binding ${candidate.binding.index} supplies a ${describeType(
            sourceType,
          )} value into a ${describeType(entry.property.logical_type)} slot. The shapes are not assignable.`,
          question: `Property "${entry.component}.${entry.property.name}" has an incompatible value shape. Is the property type wrong or the expression?`,
          subject: bindingSubject,
          evidence: [
            evidence("property declaration", "blueprint", entry.propertyPointer, entry.property.ref),
            evidence("binding property expression", "blueprint", expressionPointer),
          ],
          tags: ["type", "shape", "logical-type"],
        });
      }
    }
  }

  // A binding that references fields but reaches no source relation or step.
  for (const binding of index.bindings) {
    const fieldRefs = allBindingExpressions(binding).flatMap((expression) =>
      collectFieldRefs(expression),
    );
    if (!fieldRefs.length) continue;
    const relations = sourceRelations(binding);
    const knownRelation = relations.some((name) => index.relationByName.has(name));
    const sourceStep = hasUpstreamSourceStep(index, binding.step);
    if (knownRelation || sourceStep) continue;
    push({
      rule: "coverage.no-source",
      severity: "medium",
      title: `Binding ${binding.index} for ${binding.kind} "${binding.component}" has no source`,
      detail: `The binding references ${fieldRefs.length} field${fieldRefs.length === 1 ? "" : "s"} but declares no known source relation and no upstream source step.`,
      question: `Binding ${binding.index} reads fields without a source relation or step. Where do those fields come from?`,
      subject: {
        kind: "binding",
        name: binding.binding.debug_name ?? `${binding.component}[${binding.index}]`,
        component: binding.component,
        entityKind: binding.kind,
        bindingIndex: binding.index,
      },
      evidence: [
        evidence(
          "binding source rows",
          "blueprint",
          `${bindingPointer(binding.index)}/rows`,
        ),
        ...fieldRefs.map((field) =>
          evidence(
            `field reference ${fieldRefKey(field)}`,
            "blueprint",
            bindingPointer(binding.index),
            field,
          ),
        ),
      ],
      tags: ["coverage", "source", "lineage"],
    });
  }

  // -----------------------------------------------------------------------
  // Semantics presence
  // -----------------------------------------------------------------------

  for (const subject of index.semanticSubjects) {
    if (subject.kind === "graph") {
      const hasPurpose = nonEmpty(index.graphDeclaration?.semantics?.purpose?.text);
      if (hasPurpose || hasSemanticUnits(subject.semantics)) continue;
      // A graph with neither purpose nor units is already critical above.
      continue;
    }
    if (hasSemanticUnits(subject.semantics)) continue;
    const severity = semanticSeverity(subject.kind);
    push({
      rule: "semantics.missing",
      severity,
      title: `${subject.kind} "${subject.ownerName ?? subject.name}" has no attached semantics`,
      detail: `The ${subject.kind} carries no claims or frames. Its meaning is not stated in the snapshot.`,
      subject: semanticSubjectForFinding(subject),
      evidence: [
        evidence(
          `${subject.kind} declaration`,
          "blueprint",
          semanticPointer(index, subject),
          subject.ref,
        ),
      ],
      tags: ["semantics", "presence"],
    });
  }

  // -----------------------------------------------------------------------
  // Deterministic ordering and counts
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

  return {
    findings: sorted,
    counts,
    // The type is retained for compatibility. Audit no longer computes a rubric.
    score: { value: 0, components: [] },
    questions: sorted.filter((finding) => Boolean(finding.question)),
  };
}
