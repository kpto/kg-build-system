/**
 * Shared semantic review state.
 *
 * The sidebar, editor and bottom panel are sibling views. They must read the
 * same local decisions and sign-off approvals without a new provider in the
 * shell. This module keeps one store per snapshot, persists it through
 * `lib/reviewQueue`, and notifies every view after a change.
 *
 * It contains no React import; the views subscribe through
 * `useSyncExternalStore`.
 */

import type { DecisionStatus, ReviewApproval } from "../lib/reviewTypes";
import {
  loadSemanticApprovals,
  loadSemanticDecisions,
  saveSemanticApprovals,
  saveSemanticDecisions,
  setSemanticDecision,
  type SemanticDecisionRecord,
} from "../lib/reviewQueue";

export interface SemanticsState {
  decisions: Record<string, SemanticDecisionRecord>;
  approvals: ReviewApproval[];
  hydrated: boolean;
}

type Listener = () => void;

const states = new Map<string, SemanticsState>();
const listeners = new Map<string, Set<Listener>>();

function emptyState(): SemanticsState {
  return { decisions: {}, approvals: [], hydrated: false };
}

export function getSemanticsState(snapshotName: string): SemanticsState {
  let state = states.get(snapshotName);
  if (!state) {
    state = emptyState();
    states.set(snapshotName, state);
  }
  return state;
}

export function subscribeSemantics(
  snapshotName: string,
  listener: Listener,
): () => void {
  const set = listeners.get(snapshotName) ?? new Set<Listener>();
  set.add(listener);
  listeners.set(snapshotName, set);
  return () => {
    set.delete(listener);
  };
}

function emit(snapshotName: string, state: SemanticsState): void {
  states.set(snapshotName, state);
  for (const listener of listeners.get(snapshotName) ?? []) listener();
}

/** Read storage once after mount. SSR starts with an empty, stable state. */
export function hydrateSemantics(snapshotName: string): void {
  if (getSemanticsState(snapshotName).hydrated) return;
  const decisions = loadSemanticDecisions(snapshotName);
  const approvals = loadSemanticApprovals(snapshotName);
  emit(snapshotName, { decisions, approvals, hydrated: true });
}

export function commitSemanticDecision(
  snapshotName: string,
  key: string,
  status: DecisionStatus,
  patch: { rationale?: string; reviewer?: string; at?: string } = {},
): SemanticsState {
  const current = getSemanticsState(snapshotName);
  const decisions = setSemanticDecision(current.decisions, key, status, patch);
  saveSemanticDecisions(snapshotName, decisions);
  const next = { ...current, decisions, hydrated: true };
  emit(snapshotName, next);
  return next;
}

export function commitSemanticApproval(
  snapshotName: string,
  approval: ReviewApproval,
): SemanticsState {
  const current = getSemanticsState(snapshotName);
  const approvals = [
    approval,
    ...current.approvals.filter((entry) => entry.id !== approval.id),
  ];
  saveSemanticApprovals(snapshotName, approvals);
  const next = { ...current, approvals, hydrated: true };
  emit(snapshotName, next);
  return next;
}
