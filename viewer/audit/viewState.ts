/**
 * Shared, snapshot-scoped audit view state.
 *
 * The workbench persists the selected finding on the audit function selection.
 * Filters are presentation state for the three audit panels and must survive a
 * panel remount, so they live in this small external store rather than in one
 * component. The store holds no snapshot facts.
 */

import { useSyncExternalStore } from "react";

import type { Severity } from "@/lib/reviewTypes";
import {
  defaultAuditFilters,
  SEVERITY_ORDER,
  type AuditFilters,
} from "./auditData";

const perSnapshot = new Map<string, AuditFilters>();
const listeners = new Set<() => void>();

function stateFor(snapshotName: string): AuditFilters {
  const existing = perSnapshot.get(snapshotName);
  if (existing) return existing;
  const created = defaultAuditFilters();
  perSnapshot.set(snapshotName, created);
  return created;
}

function emit(snapshotName: string, next: AuditFilters): void {
  perSnapshot.set(snapshotName, next);
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useAuditFilters(snapshotName: string): AuditFilters {
  return useSyncExternalStore(
    subscribe,
    () => stateFor(snapshotName),
    () => stateFor(snapshotName),
  );
}

export function toggleSeverity(snapshotName: string, severity: Severity): void {
  const current = stateFor(snapshotName);
  const includes = current.severities.includes(severity);
  const all = current.severities.length === SEVERITY_ORDER.length;
  let selected: Severity[];
  if (all) {
    // From "All", a severity click focuses that severity. A second click on the
    // same chip restores the full set.
    selected = [severity];
  } else if (includes && current.severities.length === 1) {
    selected = [];
  } else {
    selected = SEVERITY_ORDER.filter((entry) =>
      entry === severity ? !includes : current.severities.includes(entry),
    );
  }
  emit(snapshotName, {
    ...current,
    // An empty severity set means "all"; a panel that hides every finding is
    // never a useful filter state.
    severities: selected.length ? selected : [...SEVERITY_ORDER],
  });
}

export function allSeverities(snapshotName: string): void {
  emit(snapshotName, {
    ...stateFor(snapshotName),
    severities: [...SEVERITY_ORDER],
  });
}

export function setGroupFilter(
  snapshotName: string,
  group: AuditFilters["group"],
): void {
  const current = stateFor(snapshotName);
  emit(snapshotName, { ...current, group, rule: null });
}

export function setRuleFilter(snapshotName: string, rule: string | null): void {
  const current = stateFor(snapshotName);
  emit(snapshotName, { ...current, rule: rule === current.rule ? null : rule });
}

export function setSubjectFilter(snapshotName: string, kind: string | null): void {
  const current = stateFor(snapshotName);
  emit(snapshotName, { ...current, subjectKind: kind });
}

export function setQuery(snapshotName: string, query: string): void {
  emit(snapshotName, { ...stateFor(snapshotName), query });
}

export function resetAuditFilters(snapshotName: string): void {
  emit(snapshotName, defaultAuditFilters());
}

/** Test hook: forget every snapshot's filter state. */
export function resetAuditViewState(): void {
  perSnapshot.clear();
  for (const listener of listeners) listener();
}
