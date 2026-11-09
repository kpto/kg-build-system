/**
 * The semantic ledger.
 *
 * The ledger is a read model over one loaded snapshot. It collects the graph
 * purpose, every attached claim, frame and limitation, and provides the review
 * decisions the snapshot makes necessary. It never infers semantics: an
 * attached unit is evidence, not a propagation rule.
 *
 * Identity rules:
 * - a unit key is the 64-bit FNV-1a digest of
 *   `graphName|subjectPath|unitKind|frameText|text`, rendered as 16 hex digits;
 * - a requirement key is stable for the subject/reason pair it describes;
 * - the snapshot digest is the same digest over canonical snapshot JSON.
 */

import { buildAudit } from "../lib/audit";
import { buildCoverage } from "../lib/coverage";
import { semanticSubjectKey } from "../lib/indexes";
import type {
  AuditFinding,
  AuditSubject,
  Decision,
  DecisionStatus,
  ReviewApproval,
  ReviewSidecar,
} from "../lib/reviewTypes";
import type {
  EntityKind,
  SemanticSubject,
  SemanticSubjectKind,
  ViewerIndex,
  ViewerSnapshot,
} from "../lib/types";
import type { SemanticDecisionRecord } from "../lib/reviewQueue";

export type SemanticUnitKind = "purpose" | "claim" | "frame" | "limitation";

export type RequirementReason =
  | "limitation"
  | "untraced-property"
  | "identity"
  | "type"
  | "abstract-producer";

/** The subject a unit is read from. Display path is stable and human-readable. */
export interface SemanticUnitSubject {
  kind: SemanticSubjectKind;
  key: string;
  name: string;
  path: string;
  ownerName?: string;
  entityKind?: EntityKind;
  bindingIndex?: number;
  assetName?: string;
}

export interface SemanticUnit {
  /** Full 64-bit FNV-1a key, 16 hex digits. */
  key: string;
  /** Display form of the key; the full key remains the identity. */
  shortKey: string;
  kind: SemanticUnitKind;
  text: string;
  graph: string;
  subject: SemanticUnitSubject;
  subjectPath: string;
  subjectKey: string;
  frame?: string;
  attached: boolean;
}

export interface RequiredDecision {
  /** Stable requirement identity; a local decision may target it directly. */
  key: string;
  reason: RequirementReason;
  title: string;
  detail: string;
  subject: AuditSubject;
  subjectPath: string;
  /** A requirement that is one semantic unit may be decided at that unit. */
  unitKey?: string;
  /** Every unit that belongs to the required subject. */
  unitKeys: string[];
  findingId?: string;
  severity?: string;
}

export interface SemanticDecision {
  id: string;
  key: string;
  title: string;
  status: DecisionStatus;
  rationale: string;
  source: "sidecar" | "queue" | "default";
  subject?: AuditSubject;
  requirementKey?: string;
  unitKey?: string;
  reviewer?: string;
  at?: string;
  tags?: string[];
}

export interface CoverageEntry extends RequiredDecision {
  decision?: SemanticDecision;
  status: DecisionStatus;
  resolved: boolean;
}

export interface SemanticCoverage {
  required: CoverageEntry[];
  total: number;
  resolved: number;
  open: number;
  subjects: AuditSubject[];
}

export interface SemanticUnitGroup {
  key: string;
  path: string;
  kind: SemanticSubjectKind;
  name: string;
  subject: SemanticUnitSubject;
  units: SemanticUnit[];
  required: number;
  open: number;
  status: DecisionStatus | "mixed" | "none";
}

export interface SignoffReadiness {
  ready: boolean;
  approved: boolean;
  blockers: string[];
  digest: string;
  shortDigest: string;
  reviewer?: string;
  at?: string;
  approval?: ReviewApproval;
  coverageOpen: number;
  unresolved: number;
}

export interface SemanticLedger {
  snapshotName: string;
  graphName: string;
  digest: string;
  shortDigest: string;
  units: SemanticUnit[];
  unitsByKey: Map<string, SemanticUnit>;
  groups: SemanticUnitGroup[];
  required: RequiredDecision[];
  decisions: SemanticDecision[];
  statusByKey: Map<string, DecisionStatus>;
  coverage: SemanticCoverage;
  signoff: SignoffReadiness;
  counts: {
    units: number;
    purpose: number;
    claims: number;
    frames: number;
    limitations: number;
    subjects: number;
    subjectsWithSemantics: number;
    required: number;
    coverageOpen: number;
    accepted: number;
    rejected: number;
    waived: number;
    open: number;
  };
}

export interface SignoffInput {
  reviewer?: string;
  at?: string;
  approvals?: ReviewApproval[];
}

// ---------------------------------------------------------------------------
// Stable identity
// ---------------------------------------------------------------------------

const FNV_OFFSET = BigInt("0xcbf29ce484222325");
const FNV_PRIME = BigInt("0x100000001b3");
const MASK_64 = BigInt("0xffffffffffffffff");

/** 64-bit FNV-1a over UTF-16 code units, stable across processes. */
export function fnv1a64(value: string): string {
  let hash = FNV_OFFSET;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= BigInt(value.charCodeAt(index));
    hash = (hash * FNV_PRIME) & MASK_64;
  }
  return hash.toString(16).padStart(16, "0");
}

/** Display form of a stable key; drops nothing from the identity itself. */
export function shortKey(value: string): string {
  return value.length > 8 ? value.slice(0, 8) : value;
}

/**
 * Stable key for one semantic unit.
 *
 * The frame text is empty for purpose, claim and frame units and carries the
 * containing frame for a limitation.
 */
export function semanticUnitKey(input: {
  graphName: string;
  subjectPath: string;
  kind: SemanticUnitKind;
  text: string;
  frameText?: string;
}): string {
  return fnv1a64(
    [
      input.graphName,
      input.subjectPath,
      input.kind,
      input.frameText ?? "",
      input.text,
    ].join("|"),
  );
}

function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const sorted: Record<string, unknown> = {};
    for (const key of Object.keys(record).sort()) {
      if (record[key] !== undefined) sorted[key] = canonical(record[key]);
    }
    return sorted;
  }
  return value;
}

/** Canonical JSON used by the content digest and the export. */
export function canonicalJson(value: unknown): string {
  return JSON.stringify(canonical(value));
}

/** 64-bit FNV-1a content digest of one snapshot. */
export function snapshotDigest(snapshot: ViewerSnapshot): string {
  return fnv1a64(canonicalJson(snapshot));
}

// ---------------------------------------------------------------------------
// Subjects
// ---------------------------------------------------------------------------

export function semanticSubjectPath(subject: SemanticSubject): string {
  switch (subject.kind) {
    case "graph":
      return `graph:${subject.name}`;
    case "field":
      return `field:${subject.ownerName ?? ""}.${subject.name}`;
    case "property":
      return `property:${subject.entityKind ?? "property"}:${
        subject.ownerName ?? ""
      }.${subject.name}`;
    case "binding":
      return `binding:${subject.bindingIndex ?? subject.name}`;
    default:
      return `${subject.kind}:${subject.name}`;
  }
}

function toUnitSubject(subject: SemanticSubject): SemanticUnitSubject {
  return {
    kind: subject.kind,
    key: subject.key,
    name: subject.name,
    path: semanticSubjectPath(subject),
    ...(subject.ownerName !== undefined ? { ownerName: subject.ownerName } : {}),
    ...(subject.entityKind !== undefined ? { entityKind: subject.entityKind } : {}),
    ...(subject.bindingIndex !== undefined
      ? { bindingIndex: subject.bindingIndex }
      : {}),
    ...(subject.assetName !== undefined ? { assetName: subject.assetName } : {}),
  };
}

/** Convert a semantic subject to the shared audit subject vocabulary. */
export function semanticAuditSubject(subject: SemanticSubject): AuditSubject {
  switch (subject.kind) {
    case "graph":
      return { kind: "graph", name: subject.name };
    case "field":
      return {
        kind: "field",
        name: subject.name,
        ...(subject.ownerName ? { component: subject.ownerName } : {}),
      };
    case "property":
      return {
        kind: "property",
        name: subject.ownerName ?? subject.name,
        ...(subject.ownerName ? { component: subject.ownerName } : {}),
        property: subject.name,
        ...(subject.entityKind ? { entityKind: subject.entityKind } : {}),
      };
    case "binding":
      return {
        kind: "binding",
        name: subject.name,
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
    default:
      return {
        kind: subject.kind,
        name: subject.name,
        component: subject.name,
      };
  }
}

export function auditSubjectKey(subject: AuditSubject | undefined): string {
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

function sameSubject(
  left: AuditSubject | undefined,
  right: AuditSubject | undefined,
): boolean {
  return Boolean(left && right) && auditSubjectKey(left) === auditSubjectKey(right);
}

// ---------------------------------------------------------------------------
// Units
// ---------------------------------------------------------------------------

function pushUnit(
  units: SemanticUnit[],
  graphName: string,
  subject: SemanticSubject,
  kind: SemanticUnitKind,
  text: string,
  frameText?: string,
): void {
  if (!text.trim()) return;
  const unitSubject = toUnitSubject(subject);
  const key = semanticUnitKey({
    graphName,
    subjectPath: unitSubject.path,
    kind,
    text,
    frameText,
  });
  units.push({
    key,
    shortKey: shortKey(key),
    kind,
    text,
    graph: graphName,
    subject: unitSubject,
    subjectPath: unitSubject.path,
    subjectKey: unitSubject.key,
    ...(frameText ? { frame: frameText } : {}),
    attached: subject.kind !== "graph",
  });
}

function collectSubjectUnits(
  units: SemanticUnit[],
  graphName: string,
  subject: SemanticSubject,
): void {
  for (const claim of subject.semantics?.claims ?? []) {
    pushUnit(units, graphName, subject, "claim", claim.text);
  }
  for (const frame of subject.semantics?.frames ?? []) {
    pushUnit(units, graphName, subject, "frame", frame.text);
    for (const limitation of frame.limitations ?? []) {
      pushUnit(units, graphName, subject, "limitation", limitation.text, frame.text);
    }
  }
}

/**
 * Collect the graph units and every attached unit in deterministic order.
 *
 * The graph purpose is one unit. Its frames and claims are read from the graph
 * declaration exactly once; the graph subject in `semanticSubjects` is not read
 * a second time.
 */
export function collectSemanticUnits(index: ViewerIndex): SemanticUnit[] {
  const declaration = index.graphDeclaration;
  const graphSubject =
    index.semanticsByKind.get("graph")?.[0] ??
    index.semanticSubjects.find((subject) => subject.kind === "graph");
  if (!declaration || !graphSubject) return [];

  const graphName = declaration.name;
  const units: SemanticUnit[] = [];
  const purpose = declaration.semantics.purpose;
  if (purpose?.text) {
    pushUnit(units, graphName, graphSubject, "purpose", purpose.text);
  }
  for (const claim of declaration.semantics.claims ?? []) {
    pushUnit(units, graphName, graphSubject, "claim", claim.text);
  }
  for (const frame of purpose?.frames ?? []) {
    pushUnit(units, graphName, graphSubject, "frame", frame.text);
    for (const limitation of frame.limitations ?? []) {
      pushUnit(units, graphName, graphSubject, "limitation", limitation.text, frame.text);
    }
  }

  for (const subject of index.semanticSubjects) {
    if (subject.kind === "graph") continue;
    collectSubjectUnits(units, graphName, subject);
  }
  return units;
}

export function groupSemanticUnits(
  units: readonly SemanticUnit[],
  required: readonly RequiredDecision[],
  statusByKey: ReadonlyMap<string, DecisionStatus>,
): SemanticUnitGroup[] {
  const groups = new Map<string, SemanticUnitGroup>();
  for (const unit of units) {
    const existing = groups.get(unit.subjectKey) ?? {
      key: unit.subjectKey,
      path: unit.subjectPath,
      kind: unit.subject.kind,
      name: unit.subject.name,
      subject: unit.subject,
      units: [],
      required: 0,
      open: 0,
      status: "none" as const,
    };
    existing.units.push(unit);
    groups.set(unit.subjectKey, existing);
  }
  for (const requirement of required) {
    const group = groups.get(
      requirement.unitKey
        ? (units.find((unit) => unit.key === requirement.unitKey)?.subjectKey ?? "")
        : "",
    );
    if (group) {
      group.required += 1;
      continue;
    }
    for (const candidate of groups.values()) {
      if (candidate.path === requirement.subjectPath) {
        candidate.required += 1;
        break;
      }
    }
  }

  for (const group of groups.values()) {
    const statuses = group.units.map(
      (unit) => statusByKey.get(unit.key) ?? "proposed",
    );
    group.open = statuses.filter((status) => status === "open").length;
    const unique = [...new Set(statuses)];
    group.status =
      !unique.length
        ? "none"
        : unique.length === 1
          ? (unique[0] as DecisionStatus)
          : statuses.includes("open")
            ? "open"
            : "mixed";
  }

  return [...groups.values()].sort((left, right) => {
    const kind = left.kind.localeCompare(right.kind);
    return kind || left.path.localeCompare(right.path);
  });
}

// ---------------------------------------------------------------------------
// Required decisions
// ---------------------------------------------------------------------------

function requirementKey(reason: RequirementReason, ...parts: string[]): string {
  return `requirement:${fnv1a64([reason, ...parts].join("|"))}`;
}

function unitsForSubject(
  units: readonly SemanticUnit[],
  path: string,
): string[] {
  return units.filter((unit) => unit.subjectPath === path).map((unit) => unit.key);
}

function isIdentityOrTypeFinding(finding: AuditFinding): boolean {
  if (/^(identity|type)\./.test(finding.rule)) return true;
  if (
    finding.rule === "nullable-identity" ||
    finding.rule === "shared-nullable-key"
  ) {
    return true;
  }
  return finding.tags.some((tag) =>
    ["identity", "type", "nullability", "presence", "shape"].includes(tag),
  );
}

function abstractRequirements(index: ViewerIndex): RequiredDecision[] {
  const requirements: RequiredDecision[] = [];
  const nodes = index.blueprint.graph?.nodes ?? [];
  const edges = index.blueprint.graph?.edges ?? [];
  const components = [
    ...nodes.map((node) => ({ kind: "node" as const, name: node.name, parent: node.parent, abstract: node.abstract === true })),
    ...edges.map((edge) => ({ kind: "edge" as const, name: edge.name, parent: edge.parent, abstract: edge.abstract === true })),
  ];

  const parentOf = new Map<string, string>();
  for (const component of components) {
    const parent = component.parent?.at(-1);
    if (parent) parentOf.set(`${component.kind}:${component.name}`, `${component.kind}:${parent}`);
  }

  const produced = new Set<string>();
  for (const binding of index.bindings) {
    produced.add(`${binding.kind}:${binding.component}`);
  }

  function hasProducedDescendant(kind: EntityKind, name: string): boolean {
    const seen = new Set<string>();
    const stack: Array<{ kind: EntityKind; name: string }> = [];
    for (const component of components) {
      if (
        parentOf.get(`${component.kind}:${component.name}`) === `${kind}:${name}`
      ) {
        stack.push({ kind: component.kind, name: component.name });
      }
    }
    while (stack.length) {
      const current = stack.pop();
      if (!current) continue;
      const id = `${current.kind}:${current.name}`;
      if (seen.has(id)) continue;
      seen.add(id);
      if (produced.has(id)) return true;
      for (const component of components) {
        if (parentOf.get(`${component.kind}:${component.name}`) === id) {
          stack.push({ kind: component.kind, name: component.name });
        }
      }
    }
    return produced.has(`${kind}:${name}`);
  }

  for (const component of components) {
    if (!component.abstract) continue;
    if (hasProducedDescendant(component.kind, component.name)) continue;
    const subject: AuditSubject = {
      kind: component.kind,
      name: component.name,
      component: component.name,
      entityKind: component.kind,
    };
    requirements.push({
      key: requirementKey("abstract-producer", component.kind, component.name),
      reason: "abstract-producer",
      title: `Abstract ${component.kind} "${component.name}" has no concrete producer`,
      detail:
        "No binding produces this abstract category or a concrete descendant of it. The category is declared, but the graph never instantiates it.",
      subject,
      subjectPath: `${component.kind}:${component.name}`,
      unitKeys: [],
      severity: "medium",
    });
  }
  return requirements;
}

/**
 * The required-decision policy.
 *
 * A decision is required for: every limitation; every property with no traced
 * source relation; every identity/type finding the audit reports; and every
 * abstract category with no concrete binding producer. The policy reads
 * existing artifacts and never invents an extra semantic unit.
 */
export function buildRequiredDecisions(
  index: ViewerIndex,
  units: readonly SemanticUnit[],
  review?: ReviewSidecar,
): RequiredDecision[] {
  const requirements = new Map<string, RequiredDecision>();

  for (const unit of units) {
    if (unit.kind !== "limitation") continue;
    requirements.set(unit.key, {
      key: unit.key,
      reason: "limitation",
      title: `Limitation on ${unit.subjectPath}`,
      detail: unit.text,
      subject: auditSubjectForUnit(unit),
      subjectPath: unit.subjectPath,
      unitKey: unit.key,
      unitKeys: [unit.key],
      severity: "info",
    });
  }

  const coverage = buildCoverage(index);
  for (const row of coverage.rows) {
    if (row.sourceRelations.length > 0) continue;
    const subject: AuditSubject = {
      kind: "property",
      name: row.component,
      component: row.component,
      property: row.property,
      entityKind: row.kind,
    };
    const subjectPath = `property:${row.kind}:${row.component}.${row.property}`;
    const key = requirementKey("untraced-property", row.kind, row.component, row.property);
    requirements.set(key, {
      key,
      reason: "untraced-property",
      title: `Property "${row.component}.${row.property}" has no traced source`,
      detail:
        row.literals > 0
          ? `The property is defined only by ${row.literals} literal value${
              row.literals === 1 ? "" : "s"
            } and no source relation.`
          : "The property has no binding or source relation, so its lineage cannot be resolved.",
      subject,
      subjectPath,
      unitKeys: unitsForSubject(units, subjectPath),
      severity: "medium",
    });
  }

  const audit = buildAudit(index, review);
  for (const finding of audit.findings) {
    if (!isIdentityOrTypeFinding(finding)) continue;
    const subject = finding.subject;
    if (!subject) continue;
    const reason: RequirementReason = finding.rule.startsWith("type.")
      ? "type"
      : "identity";
    const subjectPath = `${subject.kind}:${
      subject.component ?? subject.name
    }${subject.property ? `.${subject.property}` : ""}`;
    const key = requirementKey(reason, finding.id);
    requirements.set(key, {
      key,
      reason,
      title: finding.title,
      detail: finding.detail,
      subject,
      subjectPath,
      unitKeys: unitsForSubject(units, subjectPath),
      findingId: finding.id,
      severity: finding.severity,
    });
  }

  for (const requirement of abstractRequirements(index)) {
    requirements.set(requirement.key, requirement);
  }

  return [...requirements.values()].sort((left, right) => {
    const reason = left.reason.localeCompare(right.reason);
    if (reason) return reason;
    const path = left.subjectPath.localeCompare(right.subjectPath);
    return path || left.key.localeCompare(right.key);
  });
}

function auditSubjectForUnit(unit: SemanticUnit): AuditSubject {
  const subject = unit.subject;
  switch (subject.kind) {
    case "graph":
      return { kind: "graph", name: subject.name };
    case "property":
      return {
        kind: "property",
        name: subject.ownerName ?? subject.name,
        ...(subject.ownerName ? { component: subject.ownerName } : {}),
        property: subject.name,
        ...(subject.entityKind ? { entityKind: subject.entityKind } : {}),
      };
    case "field":
      return {
        kind: "field",
        name: subject.name,
        ...(subject.ownerName ? { component: subject.ownerName } : {}),
      };
    case "binding":
      return {
        kind: "binding",
        name: subject.name,
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
    default:
      return { kind: subject.kind, name: subject.name, component: subject.name };
  }
}

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

function sidecarDecisions(review?: ReviewSidecar): SemanticDecision[] {
  return (review?.decisions ?? []).map((decision: Decision) => ({
    id: decision.id,
    key: decision.id,
    title: decision.title,
    status: decision.status,
    rationale: decision.rationale,
    source: "sidecar" as const,
    ...(decision.subject ? { subject: decision.subject } : {}),
    ...(decision.tags ? { tags: decision.tags } : {}),
  }));
}

function queueDecisions(
  records: Record<string, SemanticDecisionRecord>,
): SemanticDecision[] {
  return Object.values(records)
    .map((record) => ({
      id: record.key,
      key: record.key,
      title: record.key,
      status: record.status,
      rationale: record.rationale ?? "",
      source: "queue" as const,
      ...(record.reviewer ? { reviewer: record.reviewer } : {}),
      ...(record.at ? { at: record.at } : {}),
    }))
    .sort((left, right) => left.key.localeCompare(right.key));
}

function decisionMatchesSubject(
  decision: SemanticDecision,
  subject: AuditSubject,
): boolean {
  return sameSubject(decision.subject, subject);
}

function findDecision(
  key: string,
  unitKeys: readonly string[],
  subjectPath: string,
  subject: AuditSubject,
  queue: Record<string, SemanticDecisionRecord>,
  sidecar: readonly SemanticDecision[],
): SemanticDecision | undefined {
  const local = queue[key];
  if (local) {
    return {
      id: key,
      key,
      title: key,
      status: local.status,
      rationale: local.rationale ?? "",
      source: "queue",
      ...(local.reviewer ? { reviewer: local.reviewer } : {}),
      ...(local.at ? { at: local.at } : {}),
    };
  }
  for (const unitKey of unitKeys) {
    const byUnit = queue[unitKey];
    if (byUnit) {
      return {
        id: unitKey,
        key: unitKey,
        title: unitKey,
        status: byUnit.status,
        rationale: byUnit.rationale ?? "",
        source: "queue",
        ...(byUnit.reviewer ? { reviewer: byUnit.reviewer } : {}),
        ...(byUnit.at ? { at: byUnit.at } : {}),
      };
    }
  }
  const byPath = queue[subjectPath] ?? queue[`subject:${subjectPath}`];
  if (byPath) {
    return {
      id: byPath.key,
      key: byPath.key,
      title: byPath.key,
      status: byPath.status,
      rationale: byPath.rationale ?? "",
      source: "queue",
      ...(byPath.reviewer ? { reviewer: byPath.reviewer } : {}),
      ...(byPath.at ? { at: byPath.at } : {}),
    };
  }
  const sidecarMatch = [...sidecar]
    .sort((left, right) => left.id.localeCompare(right.id))
    .find(
      (decision) =>
        decision.status !== "open" &&
        decisionMatchesSubject(decision, subject),
    );
  return sidecarMatch;
}

const RESOLVED_STATUSES: DecisionStatus[] = ["accepted", "rejected", "waived"];

export function isResolved(status: DecisionStatus): boolean {
  return RESOLVED_STATUSES.includes(status);
}

export function resolveCoverage(
  required: readonly RequiredDecision[],
  units: readonly SemanticUnit[],
  review: ReviewSidecar | undefined,
  local: Record<string, SemanticDecisionRecord>,
): SemanticCoverage {
  const sidecar = sidecarDecisions(review);
  const entries: CoverageEntry[] = required.map((requirement) => {
    const decision = findDecision(
      requirement.key,
      requirement.unitKeys,
      requirement.subjectPath,
      requirement.subject,
      local,
      sidecar,
    );
    const status: DecisionStatus = decision?.status ?? "open";
    const unit = requirement.unitKey
      ? units.find((candidate) => candidate.key === requirement.unitKey)
      : undefined;
    const requirementSubject = unit
      ? auditSubjectForUnit(unit)
      : requirement.subject;
    return {
      ...requirement,
      subject: requirementSubject,
      decision,
      status,
      resolved: isResolved(status),
    };
  });

  const unresolved = entries.filter((entry) => !entry.resolved);
  const subjects: AuditSubject[] = [];
  const seen = new Set<string>();
  for (const entry of unresolved) {
    const key = auditSubjectKey(entry.subject);
    if (seen.has(key)) continue;
    seen.add(key);
    subjects.push(entry.subject);
  }

  return {
    required: entries,
    total: entries.length,
    resolved: entries.length - unresolved.length,
    open: unresolved.length,
    subjects,
  };
}

export function unitStatusMap(
  units: readonly SemanticUnit[],
  required: readonly RequiredDecision[],
  review: ReviewSidecar | undefined,
  local: Record<string, SemanticDecisionRecord>,
): Map<string, DecisionStatus> {
  const sidecar = sidecarDecisions(review);
  const requiredByUnit = new Set(
    required.map((requirement) => requirement.unitKey).filter(Boolean) as string[],
  );
  const statuses = new Map<string, DecisionStatus>();
  for (const unit of units) {
    const direct = findDecision(
      unit.key,
      [],
      unit.subjectPath,
      auditSubjectForUnit(unit),
      local,
      sidecar,
    );
    if (direct) {
      statuses.set(unit.key, direct.status);
    } else {
      statuses.set(unit.key, requiredByUnit.has(unit.key) ? "open" : "proposed");
    }
  }
  return statuses;
}

// ---------------------------------------------------------------------------
// Sign-off
// ---------------------------------------------------------------------------

export function assessSignoff(
  coverage: SemanticCoverage,
  digest: string,
  input: SignoffInput = {},
): SignoffReadiness {
  const approvals = input.approvals ?? [];
  const matching = approvals
    .filter((approval) => approval.status === "signed-off" && approval.digest === digest)
    .sort((left, right) => right.at.localeCompare(left.at));
  const approval = matching[0];
  const reviewer = input.reviewer?.trim() || approval?.reviewer;
  const at = input.at?.trim() || approval?.at;

  const blockers: string[] = [];
  if (coverage.open > 0) {
    blockers.push(
      `${coverage.open} required decision${coverage.open === 1 ? "" : "s"} unresolved`,
    );
  }
  if (!digest) blockers.push("No snapshot digest");
  if (!reviewer) blockers.push("No reviewer");
  if (!at) blockers.push("No sign-off timestamp");

  const ready = blockers.length === 0;
  return {
    ready,
    approved: Boolean(approval && ready),
    blockers,
    digest,
    shortDigest: shortKey(digest),
    ...(reviewer ? { reviewer } : {}),
    ...(at ? { at } : {}),
    ...(approval ? { approval } : {}),
    coverageOpen: coverage.open,
    unresolved: coverage.open,
  };
}

export function buildSignoffApproval(
  digest: string,
  coverage: SemanticCoverage,
  reviewer: string,
  at: string,
  note?: string,
): ReviewApproval {
  return {
    id: `approval:${fnv1a64([digest, reviewer.trim(), at, coverage.open].join("|"))}`,
    scope: coverage.required.map((entry) => entry.subject),
    digest,
    reviewer: reviewer.trim(),
    at,
    status: "signed-off",
    ...(note?.trim() ? { note: note.trim() } : {}),
  };
}

// ---------------------------------------------------------------------------
// Ledger
// ---------------------------------------------------------------------------

export function buildSemanticLedger(
  index: ViewerIndex,
  review?: ReviewSidecar,
  local: Record<string, SemanticDecisionRecord> = {},
  signoff: SignoffInput = {},
): SemanticLedger {
  const graphName = index.graphDeclaration?.name ?? "";
  const units = collectSemanticUnits(index);
  const unitsByKey = new Map(units.map((unit) => [unit.key, unit]));
  const required = buildRequiredDecisions(index, units, review);
  const coverage = resolveCoverage(required, units, review, local);
  const statusByKey = unitStatusMap(units, required, review, local);
  const groups = groupSemanticUnits(units, required, statusByKey);
  const decisions = [...sidecarDecisions(review), ...queueDecisions(local)];
  const digest = snapshotDigest(index.snapshot);

  const counts = {
    units: units.length,
    purpose: units.filter((unit) => unit.kind === "purpose").length,
    claims: units.filter((unit) => unit.kind === "claim").length,
    frames: units.filter((unit) => unit.kind === "frame").length,
    limitations: units.filter((unit) => unit.kind === "limitation").length,
    subjects: groups.length,
    subjectsWithSemantics: groups.length,
    required: required.length,
    coverageOpen: coverage.open,
    accepted: [...statusByKey.values()].filter((status) => status === "accepted").length,
    rejected: [...statusByKey.values()].filter((status) => status === "rejected").length,
    waived: [...statusByKey.values()].filter((status) => status === "waived").length,
    open: [...statusByKey.values()].filter((status) => status === "open").length,
  };

  return {
    snapshotName: index.snapshot.name,
    graphName,
    digest,
    shortDigest: shortKey(digest),
    units,
    unitsByKey,
    groups,
    required,
    decisions,
    statusByKey,
    coverage,
    signoff: assessSignoff(coverage, digest, signoff),
    counts,
  };
}

/** Plain JSON payload for the review export and the Data tab. */
export function semanticReviewExport(
  ledger: SemanticLedger,
  options: { reviewer?: string; at?: string; approvals?: ReviewApproval[] } = {},
): unknown {
  return {
    format: "kg-viewer-semantic-review",
    version: 1,
    snapshot: {
      name: ledger.snapshotName,
      digest: ledger.digest,
    },
    generatedAt: options.at ?? null,
    reviewer: options.reviewer ?? null,
    counts: ledger.counts,
    units: ledger.units,
    required: ledger.required,
    coverage: {
      total: ledger.coverage.total,
      resolved: ledger.coverage.resolved,
      open: ledger.coverage.open,
      unresolvedSubjects: ledger.coverage.subjects,
    },
    decisions: ledger.decisions,
    approvals: options.approvals ?? [],
    signoff: ledger.signoff,
  };
}

/** Find a ledger unit by the workbench selection's unit key. */
export function selectedUnit(
  ledger: SemanticLedger,
  unitKey: string | undefined,
): SemanticUnit | undefined {
  if (!unitKey) return undefined;
  return ledger.unitsByKey.get(unitKey);
}

/** The first unit of a subject, used when a subject row is selected. */
export function firstUnitForSubject(
  ledger: SemanticLedger,
  subjectPath: string,
): SemanticUnit | undefined {
  return ledger.units.find((unit) => unit.subjectPath === subjectPath);
}

/** The first required unit, or the first unit, as the editor fallback. */
export function defaultSemanticUnit(ledger: SemanticLedger): SemanticUnit | undefined {
  const requiredUnit = ledger.units.find((unit) =>
    ledger.required.some((requirement) => requirement.unitKey === unit.key),
  );
  return requiredUnit ?? ledger.units[0];
}

/** Map a subject back to the semantic subject key the index uses. */
export function semanticSubjectLookupKey(
  kind: SemanticSubjectKind,
  ...segments: Array<string | number>
): string {
  return semanticSubjectKey(kind, ...segments);
}

/** A compact status label shared by the sidebar, editor and bottom panel. */
export function decisionLabel(status: DecisionStatus): string {
  switch (status) {
    case "accepted":
      return "Accepted";
    case "rejected":
      return "Rejected";
    case "waived":
      return "Waived";
    case "proposed":
      return "Proposed";
    default:
      return "Open";
  }
}
