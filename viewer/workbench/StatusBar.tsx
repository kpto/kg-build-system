"use client";

import { useCallback, useMemo, useSyncExternalStore } from "react";
import { CircleDot, Database, Minus, Plus } from "lucide-react";

import { buildSemanticLedger } from "@/semantics/model";
import { getSemanticsState, subscribeSemantics } from "@/semantics/store";
import { ACTIVITY_LABELS } from "./defaults";
import { useWorkbench } from "./store";
import type { WorkbenchSelection } from "./types";

export interface StatusBarProps {
  zoom: number;
  onZoomIn(): void;
  onZoomOut(): void;
  onZoomReset(): void;
}

function selectedSubject(selection: WorkbenchSelection): string {
  if (selection.stepId) return selection.stepId.join(" / ");
  if (selection.component && selection.property) {
    return `${selection.component}.${selection.property}`;
  }
  if (selection.component) return selection.component;
  if (selection.name) return selection.name;
  if (selection.findingId) return selection.findingId;
  if (selection.unitKey) return selection.unitKey;
  if (selection.kind) return selection.kind;
  return "No subject selected";
}

export function StatusBar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
}: StatusBarProps) {
  const { state } = useWorkbench();
  const snapshotName = state.snapshot.name;
  const local = useSyncExternalStore(
    useCallback(
      (listener: () => void) => subscribeSemantics(snapshotName, listener),
      [snapshotName],
    ),
    useCallback(() => getSemanticsState(snapshotName), [snapshotName]),
    useCallback(() => getSemanticsState(snapshotName), [snapshotName]),
  );
  const ledger = useMemo(
    () => buildSemanticLedger(state.index, state.review, local.decisions),
    [state.index, state.review, local.decisions],
  );
  const coverage = ledger.coverage;
  const accepted = coverage.required.filter(
    (entry) => entry.status === "accepted",
  ).length;
  const rejected = coverage.required.filter(
    (entry) => entry.status === "rejected",
  ).length;
  const waived = coverage.required.filter(
    (entry) => entry.status === "waived",
  ).length;
  const open = coverage.open;

  const selection = state.functions[state.activity].selection;

  return (
    <footer className="wb-statusbar" aria-label="Workbench status">
      <div className="wb-status-cluster">
        <span className="wb-status-item" title={state.snapshot.title}>
          <Database aria-hidden className="size-3" />
          <span className="wb-mono">{state.snapshot.name}</span>
        </span>
        <span className="wb-status-divider" aria-hidden />
        <span className="wb-status-item" title={`${ACTIVITY_LABELS[state.activity]} selection`}>
          <CircleDot aria-hidden className="size-3" />
          <span className="wb-status-label">{ACTIVITY_LABELS[state.activity]}</span>
          <span className="wb-mono wb-status-subject">{selectedSubject(selection)}</span>
        </span>
      </div>

      <div className="wb-status-cluster wb-status-trailing">
        <span
          className="wb-status-item"
          title="Required decisions in the semantic ledger"
        >
          <span className="wb-status-dot" data-state="accepted" aria-hidden />
          {accepted} accepted
          <span className="wb-status-dot" data-state="open" aria-hidden />
          {open} open
          <span className="wb-status-dot" data-state="rejected" aria-hidden />
          {rejected} rejected
          {waived ? (
            <>
              <span className="wb-status-dot" data-state="waived" aria-hidden />
              {waived} waived
            </>
          ) : null}
        </span>
        <span className="wb-status-divider" aria-hidden />
        <span
          className="wb-status-item wb-mono"
          title="Required decisions resolved / total required. The Semantics feature owns the ledger."
        >
          Coverage {coverage.resolved}/{coverage.total}
        </span>
        <span className="wb-status-divider" aria-hidden />
        <span className="wb-status-item" title="Compile-only snapshot">
          compile-only
        </span>
        <span className="wb-status-divider" aria-hidden />
        <span className="wb-zoom" role="group" aria-label="Interface zoom">
          <button
            type="button"
            className="wb-status-button"
            onClick={onZoomOut}
            aria-label="Zoom out"
            title="Zoom out"
            disabled={zoom <= 0.8}
          >
            <Minus aria-hidden className="size-3" />
          </button>
          <button
            type="button"
            className="wb-status-button wb-zoom-value"
            onClick={onZoomReset}
            aria-label="Reset zoom to 100 percent"
            title="Reset zoom to 100%"
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            className="wb-status-button"
            onClick={onZoomIn}
            aria-label="Zoom in"
            title="Zoom in"
            disabled={zoom >= 1.3}
          >
            <Plus aria-hidden className="size-3" />
          </button>
        </span>
      </div>
    </footer>
  );
}
