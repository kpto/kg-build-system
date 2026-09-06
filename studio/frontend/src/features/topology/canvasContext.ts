"use client";

import { createContext, useContext } from "react";

/**
 * The imperative bridge between the canvas and the chrome around it.
 *
 * The React Flow instance lives inside the provider, but the "+" button, the scope
 * strip's search and the inspector all need to reach it (select, centre a ref, request
 * the add / name flows). Rather than thread handlers through every child, the canvas
 * publishes a small command object here once, and consumers read it. It is recreated
 * whenever its closures change, so callers must read it at call time (inside a handler),
 * never capture it in a memoised dependency list.
 */
export interface TopologyCanvasApi {
  /** Move the global selection (the inspector and every badge follow it). */
  onSelectRef(ref: string | null): void;
  /** React to a vertex being clicked on the canvas (keeps the node focused). */
  onNodeClick(id: string): void;
  /** Centre a component id in the viewport. No-op when it is off-canvas/filtered. */
  reveal(id: string): void;
  /** Open the add-node flow, optionally pre-seeded with a kind. */
  openAddNode(): void;
  /** A ref became selected elsewhere (problem badge, search) — scroll it into view. */
  revealRef(ref: string | null): void;
}

const CanvasContext = createContext<TopologyCanvasApi | null>(null);

export const CanvasProvider = CanvasContext.Provider;

/** The canvas API; throws only if used outside the topology canvas (never at rest). */
export function useTopologyCanvas(): TopologyCanvasApi {
  const api = useContext(CanvasContext);
  if (!api) throw new Error("useTopologyCanvas must be used inside the topology canvas");
  return api;
}
