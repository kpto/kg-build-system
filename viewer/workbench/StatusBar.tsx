"use client";

import { CircleDot, Database, Minus, Plus } from "lucide-react";

import { ACTIVITY_LABELS } from "./defaults";
import { useWorkbench } from "./store";
import { currentLensSelection, currentSelection } from "./types";
import type { WorkbenchSelection } from "./types";

export interface StatusBarProps {
  zoom: number;
  onZoomIn(): void;
  onZoomOut(): void;
  onZoomReset(): void;
}

function displayIdentity(value: string): string {
  // Meaning selections carry their stable subject key; the NUL separator is an
  // identity delimiter, not display text.
  return value.replace(/\u0000/g, " / ");
}

function selectedSubject(selection: WorkbenchSelection): string {
  if (selection.stepId) return selection.stepId.join(" / ");
  if (selection.component && selection.property) {
    return `${displayIdentity(selection.component)}.${selection.property}`;
  }
  if (selection.component) return displayIdentity(selection.component);
  if (selection.name) return selection.name;
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
  const stats = state.index.stats;
  const selection =
    state.activity === "topology"
      ? currentLensSelection(state)
      : currentSelection(state);

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
        <span className="wb-status-item wb-mono" title="Topology nodes">
          {stats.topologyNodes} nodes
        </span>
        <span className="wb-status-item wb-mono" title="Topology edges">
          {stats.topologyEdges} edges
        </span>
        <span className="wb-status-item wb-mono" title="Bindings">
          {stats.bindings} bindings
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
