/**
 * Types for the review, audit and understanding surfaces.
 *
 * Every value below is derived from a loaded snapshot or from the optional
 * review sidecar. Nothing here executes a build or calls a model.
 */

import type { EntityKind, StepId } from "./types";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

/** A pointer into one of the loaded artifacts, addressed as RFC 6901. */
export interface EvidenceRef {
  label: string;
  artifact: "blueprint" | "workflow" | "report" | "metaGraph";
  jsonPointer: string;
  ref?: string[];
}

export interface AuditSubject {
  kind:
    | "property"
    | "node"
    | "edge"
    | "binding"
    | "step"
    | "asset"
    | "relation"
    | "projection";
  name: string;
  component?: string;
  property?: string;
  entityKind?: EntityKind;
  bindingIndex?: number;
  stepId?: StepId;
}

export interface AuditFinding {
  /** Stable hash of rule + subject + evidence pointers. */
  id: string;
  rule: string;
  severity: Severity;
  title: string;
  detail: string;
  question?: string;
  subject?: AuditSubject;
  evidence: EvidenceRef[];
  tags: string[];
}

export interface AuditScoreComponent {
  id: string;
  label: string;
  value: number;
  weight: number;
  detail: string;
}

export interface AuditReport {
  findings: AuditFinding[];
  counts: Record<Severity, number>;
  score: { value: number; components: AuditScoreComponent[] };
  /** Exactly the findings that carry a design question. */
  questions: AuditFinding[];
}

export interface CoverageCell {
  component: string;
  kind: EntityKind;
  property: string;
  bindings: number;
  tracedFields: number;
  literals: number;
  sourceRelations: string[];
  steps: StepId[];
}

export interface CoverageMatrix {
  rows: Array<{
    component: string;
    kind: EntityKind;
    property: string;
    cells: Array<{
      source: string;
      fields: number;
      literals: number;
      bindings: number;
    }>;
    tracedFields: number;
    literals: number;
    sourceRelations: string[];
    steps: StepId[];
  }>;
  sources: string[];
}

export interface Impact {
  subject: AuditSubject;
  upstream: StepId[];
  downstream: StepId[];
  artifacts: string[];
  nodes: string[];
  edges: string[];
  /** Terminal component names: `file`, `meta_graph` and `neo4j`. */
  targets: string[];
  records?: number;
}

export type DecisionStatus = "proposed" | "accepted" | "rejected" | "open";

export interface Decision {
  id: string;
  title: string;
  status: DecisionStatus;
  rationale: string;
  evidence: EvidenceRef[];
  subject?: AuditSubject;
  tags?: string[];
}

export interface ReviewSidecar {
  format: "kg-viewer-review";
  version: 1;
  ai?: {
    model?: string;
    runId?: string;
    generatedAt?: string;
    note?: string;
  };
  decisions: Decision[];
  notes?: Array<{
    id: string;
    author?: string;
    text: string;
    createdAt?: string;
    subject?: AuditSubject;
  }>;
}

export interface DecisionView extends Decision {
  source: "sidecar" | "derived";
  rationaleSupplied: boolean;
}

export type ReviewStatus = "open" | "acknowledged" | "waived" | "resolved";

export interface ReviewRecord {
  findingId: string;
  status: ReviewStatus;
  note?: string;
}

export interface ReviewQueueSummary {
  total: number;
  open: number;
  acknowledged: number;
  waived: number;
  resolved: number;
}

export interface SnapshotDiff {
  summary: {
    stepsAdded: number;
    stepsRemoved: number;
    connectionsAdded: number;
    connectionsRemoved: number;
    nodesAdded: number;
    nodesRemoved: number;
    edgesAdded: number;
    edgesRemoved: number;
    bindingsAdded: number;
    bindingsRemoved: number;
    propertiesChanged: number;
  };
  steps: { added: StepId[]; removed: StepId[]; changed: StepId[] };
  connections: { added: string[]; removed: string[] };
  topology: { added: string[]; removed: string[] };
  bindings: { added: number[]; removed: number[]; changed: number[] };
}
