/**
 * Review queue persistence.
 *
 * Records live in localStorage keyed by snapshot name and finding id. The module
 * is safe to import during SSR: every read returns an empty queue and every
 * write is a no-op when no browser is present. A waiver without a note is
 * refused because a waiver is a review decision that must be explained.
 */

import type { AuditReport, ReviewQueueSummary, ReviewRecord, ReviewStatus } from "./reviewTypes";

export const KEY_PREFIX = "kg-viewer:review:";

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
