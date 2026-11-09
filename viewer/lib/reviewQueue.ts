/**
 * Review queue persistence.
 *
 * Records live in localStorage keyed by snapshot name and finding id. The module
 * is safe to import during SSR: every read returns an empty queue and every
 * write is a no-op when no browser is present. A waiver without a note is
 * refused because a waiver is a review decision that must be explained.
 */

import type {
  AuditReport,
  DecisionStatus,
  ReviewApproval,
  ReviewQueueSummary,
  ReviewRecord,
  ReviewStatus,
} from "./reviewTypes";

export const KEY_PREFIX = "kg-viewer:review:";
export const SEMANTIC_DECISION_PREFIX = "kg-viewer:semantics:decision:";
export const SEMANTIC_APPROVAL_PREFIX = "kg-viewer:semantics:approval:";

/**
 * One local semantic decision.
 *
 * The semantic ledger keys a decision by the stable unit key or requirement
 * key, never by an array position.
 */
export interface SemanticDecisionRecord {
  key: string;
  status: DecisionStatus;
  rationale?: string;
  reviewer?: string;
  at?: string;
}

const DECISION_STATUSES: DecisionStatus[] = [
  "proposed",
  "accepted",
  "rejected",
  "waived",
  "open",
];

const STATUSES: ReviewStatus[] = [
  "open",
  "acknowledged",
  "waived",
  "resolved",
];

function isObject(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function isReviewStatus(value: unknown): value is ReviewStatus {
  return typeof value === "string" && (STATUSES as string[]).includes(value);
}

export function queueKey(snapshotName: string): string {
  return `${KEY_PREFIX}${snapshotName}`;
}

export function loadReviewQueue(
  snapshotName: string,
): Record<string, ReviewRecord> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(queueKey(snapshotName));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!isObject(parsed)) return {};
    const records: Record<string, ReviewRecord> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (!isObject(value) || !isReviewStatus(value.status)) continue;
      const findingId = typeof value.findingId === "string" ? value.findingId : key;
      records[findingId] = {
        findingId,
        status: value.status,
        ...(typeof value.note === "string" && value.note.trim()
          ? { note: value.note }
          : {}),
      };
    }
    return records;
  } catch {
    return {};
  }
}

export function saveReviewQueue(
  snapshotName: string,
  records: Record<string, ReviewRecord>,
): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(queueKey(snapshotName), JSON.stringify(records));
  } catch {
    // Storage can be unavailable (private mode, quota). The in-memory queue
    // still works for the current session.
  }
}

export function setReviewStatus(
  records: Record<string, ReviewRecord>,
  findingId: string,
  status: ReviewStatus,
  note?: string,
): Record<string, ReviewRecord> {
  const existing = records[findingId];
  const effectiveNote = note !== undefined ? note : existing?.note;
  if (status === "waived" && (!effectiveNote || !effectiveNote.trim())) {
    throw new Error("A waiver requires a note");
  }
  const trimmed = effectiveNote?.trim();
  return {
    ...records,
    [findingId]: {
      findingId,
      status,
      ...(trimmed ? { note: trimmed } : {}),
    },
  };
}

export function summarizeQueue(
  audit: AuditReport,
  records: Record<string, ReviewRecord>,
): ReviewQueueSummary {
  const summary: ReviewQueueSummary = {
    total: audit.findings.length,
    open: 0,
    acknowledged: 0,
    waived: 0,
    resolved: 0,
  };
  for (const finding of audit.findings) {
    const status = records[finding.id]?.status ?? "open";
    summary[status] += 1;
  }
  return summary;
}

// ---------------------------------------------------------------------------
// Semantic ledger decisions
// ---------------------------------------------------------------------------

export function semanticDecisionKey(snapshotName: string): string {
  return `${SEMANTIC_DECISION_PREFIX}${snapshotName}`;
}

export function semanticApprovalKey(snapshotName: string): string {
  return `${SEMANTIC_APPROVAL_PREFIX}${snapshotName}`;
}

function isDecisionStatus(value: unknown): value is DecisionStatus {
  return typeof value === "string" && (DECISION_STATUSES as string[]).includes(value);
}

/** Read local semantic decisions. SSR returns an empty ledger. */
export function loadSemanticDecisions(
  snapshotName: string,
): Record<string, SemanticDecisionRecord> {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(semanticDecisionKey(snapshotName));
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (!isObject(parsed)) return {};
    const records: Record<string, SemanticDecisionRecord> = {};
    for (const [key, value] of Object.entries(parsed)) {
      if (!isObject(value) || !isDecisionStatus(value.status)) continue;
      records[key] = {
        key,
        status: value.status,
        ...(typeof value.rationale === "string" && value.rationale.trim()
          ? { rationale: value.rationale.trim() }
          : {}),
        ...(typeof value.reviewer === "string" && value.reviewer.trim()
          ? { reviewer: value.reviewer.trim() }
          : {}),
        ...(typeof value.at === "string" && value.at.trim() ? { at: value.at } : {}),
      };
    }
    return records;
  } catch {
    return {};
  }
}

export function saveSemanticDecisions(
  snapshotName: string,
  records: Record<string, SemanticDecisionRecord>,
): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      semanticDecisionKey(snapshotName),
      JSON.stringify(records),
    );
  } catch {
    // Storage is optional; the in-memory ledger still answers the session.
  }
}

/**
 * Record one semantic decision.
 *
 * A waiver is a decision that must be explained, so it requires a rationale or
 * an explicit reviewer note. The rule mirrors the review queue's waiver rule.
 */
export function setSemanticDecision(
  records: Record<string, SemanticDecisionRecord>,
  key: string,
  status: DecisionStatus,
  patch: { rationale?: string; reviewer?: string; at?: string } = {},
): Record<string, SemanticDecisionRecord> {
  const existing = records[key];
  const rationale =
    patch.rationale !== undefined ? patch.rationale : (existing?.rationale ?? "");
  const trimmed = rationale.trim();
  if (status === "waived" && !trimmed) {
    throw new Error("A semantic waiver requires a rationale");
  }
  return {
    ...records,
    [key]: {
      key,
      status,
      ...(trimmed ? { rationale: trimmed } : {}),
      ...(patch.reviewer !== undefined
        ? patch.reviewer.trim()
          ? { reviewer: patch.reviewer.trim() }
          : {}
        : existing?.reviewer
          ? { reviewer: existing.reviewer }
          : {}),
      ...(patch.at !== undefined
        ? patch.at.trim()
          ? { at: patch.at }
          : {}
        : existing?.at
          ? { at: existing.at }
          : {}),
    },
  };
}

/** Read sign-off approvals. SSR returns an empty list. */
export function loadSemanticApprovals(snapshotName: string): ReviewApproval[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(semanticApprovalKey(snapshotName));
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isApproval);
  } catch {
    return [];
  }
}

export function saveSemanticApprovals(
  snapshotName: string,
  approvals: ReviewApproval[],
): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      semanticApprovalKey(snapshotName),
      JSON.stringify(approvals),
    );
  } catch {
    // Storage is optional; the approval is still held by the workbench state.
  }
}

function isApproval(value: unknown): value is ReviewApproval {
  if (!isObject(value)) return false;
  return (
    typeof value.id === "string" &&
    typeof value.digest === "string" &&
    typeof value.reviewer === "string" &&
    typeof value.at === "string" &&
    (value.status === "draft" ||
      value.status === "signed-off" ||
      value.status === "revoked") &&
    Array.isArray(value.scope)
  );
}
