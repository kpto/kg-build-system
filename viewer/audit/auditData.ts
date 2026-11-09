/**
 * Audit data access.
 *
 * `buildAudit` is pure, so the three audit panels share one report per loaded
 * index. The cache is keyed by the index object; a new snapshot produces a new
 * index and therefore a new report.
 */

import { auditRuleGroup, buildAudit, type AuditRuleGroupId } from "@/lib/audit";
import type {
  AuditFinding,
  AuditReport,
  AuditSubject,
  Decision,
  ReviewSidecar,
  Severity,
} from "@/lib/reviewTypes";
import type { ViewerIndex } from "@/lib/types";
import type { WorkbenchSelection } from "@/workbench/types";

const reports = new WeakMap<ViewerIndex, AuditReport>();

export function auditReportFor(
  index: ViewerIndex,
  review?: ReviewSidecar,
): AuditReport {
  const cached = reports.get(index);
  if (cached) return cached;
  const report = buildAudit(index, review);
  reports.set(index, report);
  return report;
}

export interface AuditFilters {
  severities: Severity[];
  /** Focused rule group; `identity` is the default review queue. */
  group: AuditRuleGroupId | null;
  rule: string | null;
  subjectKind: string | null;
  query: string;
}

export const SEVERITY_ORDER: Severity[] = [
  "critical",
  "high",
  "medium",
  "low",
  "info",
];

export const DEFAULT_AUDIT_GROUP: AuditRuleGroupId = "identity";

export function defaultAuditFilters(): AuditFilters {
  return {
    severities: [...SEVERITY_ORDER],
    group: DEFAULT_AUDIT_GROUP,
    rule: null,
    subjectKind: null,
    query: "",
  };
}

export function findingSubjectKind(finding: AuditFinding): string {
  const subject = finding.subject;
  if (!subject) return "graph";
  return subject.kind;
}

export function filterAuditFindings(
  findings: readonly AuditFinding[],
  filters: AuditFilters,
): AuditFinding[] {
  const query = filters.query.trim().toLowerCase();
  return findings.filter((finding) => {
    if (!filters.severities.includes(finding.severity)) return false;
    if (filters.rule) {
      if (finding.rule !== filters.rule) return false;
    } else if (
      filters.group &&
      auditRuleGroup(finding.rule) !== filters.group
    ) {
      return false;
    }
    if (
      filters.subjectKind &&
      findingSubjectKind(finding) !== filters.subjectKind
    ) {
      return false;
    }
    if (!query) return true;
    const haystack = [
      finding.rule,
      finding.title,
      finding.detail,
      finding.subject?.name,
      finding.subject?.component,
      finding.subject?.property,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(query);
  });
}

export function countBySubject(
  findings: readonly AuditFinding[],
): Array<{ kind: string; count: number }> {
  const counts = new Map<string, number>();
  for (const finding of findings) {
    const kind = findingSubjectKind(finding);
    counts.set(kind, (counts.get(kind) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([kind, count]) => ({ kind, count }))
    .sort((left, right) => right.count - left.count || left.kind.localeCompare(right.kind));
}

export function subjectLabel(finding: AuditFinding): string {
  const subject = finding.subject;
  if (!subject) return "graph";
  if (subject.kind === "property") {
    return `${subject.entityKind ?? "property"} ${subject.component ?? subject.name}.${
      subject.property ?? ""
    }`;
  }
  if (subject.kind === "field") {
    return `field ${subject.component ? `${subject.component}.` : ""}${subject.name}`;
  }
  if (subject.kind === "graph" || subject.kind === "struct") {
    return `${subject.kind} ${subject.name}`;
  }
  if (subject.component && subject.component !== subject.name) {
    return `${subject.kind} ${subject.component}`;
  }
  return `${subject.kind} ${subject.name}`;
}

function sameSubject(left: AuditSubject | undefined, right: AuditSubject | undefined): boolean {
  if (!left || !right) return false;
  return (
    left.kind === right.kind &&
    left.name === right.name &&
    left.component === right.component &&
    left.property === right.property &&
    left.entityKind === right.entityKind &&
    left.bindingIndex === right.bindingIndex &&
    (left.stepId?.join("/") ?? "") === (right.stepId?.join("/") ?? "")
  );
}

/** The review decision attached to a finding's subject, if the sidecar has one. */
export function decisionForFinding(
  review: ReviewSidecar,
  finding: AuditFinding | undefined,
): Decision | undefined {
  if (!finding?.subject) return undefined;
  return review.decisions.find((decision) =>
    sameSubject(decision.subject, finding.subject),
  );
}

/**
 * Resolve the finding the editor and bottom panels display.
 *
 * A selection that still exists but is hidden by the current filters is kept,
 * so changing a filter does not silently change the detail pane. Otherwise the
 * first visible finding is used.
 */
export function activeFinding(
  report: AuditReport,
  filtered: readonly AuditFinding[],
  selectedId: string | undefined,
): AuditFinding | undefined {
  if (selectedId) {
    const selected =
      filtered.find((finding) => finding.id === selectedId) ??
      report.findings.find((finding) => finding.id === selectedId);
    if (selected) return selected;
  }
  return filtered[0];
}

/** The proof function selection that opens the finding's subject. */
export function proofSelectionFor(finding: AuditFinding): WorkbenchSelection | null {
  const subject = finding.subject;
  if (!subject) return null;
  const base: WorkbenchSelection = { activity: "proof" };
  switch (subject.kind) {
    case "property":
      return {
        ...base,
        kind: "property",
        name: subject.component ?? subject.name,
        component: subject.component ?? subject.name,
        property: subject.property,
        level: "property",
      };
    case "node":
      return {
        ...base,
        kind: "node",
        name: subject.name,
        component: subject.name,
        level: "node",
      };
    case "edge":
      return {
        ...base,
        kind: "edge",
        name: subject.name,
        component: subject.name,
        level: "edge",
      };
    case "asset":
      return {
        ...base,
        kind: "asset",
        name: subject.name,
        component: subject.name,
        level: "asset",
      };
    case "relation":
      return {
        ...base,
        kind: "relation",
        name: subject.name,
        component: subject.name,
      };
    case "projection":
      return {
        ...base,
        kind: "projection",
        name: subject.name,
        component: subject.name,
      };
    case "binding":
      return {
        ...base,
        kind: "binding",
        name: subject.name,
        component: subject.component ?? subject.name,
      };
    case "step":
      return {
        ...base,
        kind: "step",
        name: subject.name,
        component: subject.component ?? subject.name,
        ...(subject.stepId ? { stepId: subject.stepId } : {}),
      };
    case "field":
      return {
        ...base,
        kind: "field",
        name: subject.name,
        component: subject.component ?? subject.name,
      };
    default:
      return null;
  }
}
