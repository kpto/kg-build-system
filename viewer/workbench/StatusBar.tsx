"use client";

import { AlertTriangle, CircleDot, Minus, Plus } from "lucide-react";

import { useWorkbench } from "./store";
import { activeDocument, lensSelection } from "./types";
import type { SubjectSelection } from "./types";

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

function selectedSubject(selection: SubjectSelection | undefined): string {
  if (!selection) return "";
  if (selection.stepId) return selection.stepId.join(" / ");
  if (selection.component && selection.property) {
    return `${displayIdentity(selection.component)}.${selection.property}`;
  }
  if (selection.component) return displayIdentity(selection.component);
  if (selection.name) return selection.name;
  return "";
}

export function StatusBar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
}: StatusBarProps) {
  const { state } = useWorkbench();
  const stats = state.index.stats;
  const selection = lensSelection(state);
  const document = activeDocument(state);
  const documentLabel =
    document.kind === "graph"
      ? "Graph"
      : document.kind === "workflow"
        ? "Workflow"
        : selection?.kind === "step"
          ? "Step"
          : "Subject";
  const subjectLabel =
    document.kind === "workflow"
      ? `${state.index.workflow.steps.length} steps / ${state.index.workflow.connections.length} connections`
      : selectedSubject(selection);
  const failures = state.snapshot.report?.unresolved_failures.length ?? 0;

  return (
    <footer className="wb-statusbar" aria-label="Workbench status">
      <div className="wb-status-cluster">
        <span className="wb-status-item" title="Active document selection">
          <CircleDot aria-hidden className="size-3" />
          <span className="wb-status-label">{documentLabel}</span>
          {subjectLabel ? (
            <span className="wb-status-subject">{subjectLabel}</span>
          ) : null}
        </span>
        {failures ? (
          <span
            className="wb-status-item wb-status-failure"
            title={`${failures} unresolved build ${
              failures === 1 ? "failure" : "failures"
            }`}
          >
            <AlertTriangle aria-hidden className="size-3" />
            {failures} unresolved
          </span>
        ) : null}
      </div>

      <div className="wb-status-cluster wb-status-trailing">
        <span className="wb-status-item" title="Topology nodes">
          {stats.topologyNodes} nodes
        </span>
        <span className="wb-status-item" title="Topology edges">
          {stats.topologyEdges} edges
        </span>
        <span className="wb-status-item" title="Bindings">
          {stats.bindings} bindings
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
