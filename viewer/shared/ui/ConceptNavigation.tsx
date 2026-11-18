"use client";

import { createContext, useContext, type ReactNode } from "react";

import type { ConceptTarget } from "@/lib/concepts";

/**
 * The application's concept navigation. The workbench provides it once, and a
 * pill calls it directly; no parent passes a click handler or knows how to
 * resolve an instance name to a document.
 */
export interface ConceptNavigation {
  /** Open a target; a background open appends a permanent tab without
   * activating it and leaves the current view in place. */
  open(target: ConceptTarget, options?: { background?: boolean }): void;
}

const ConceptNavigationContext = createContext<ConceptNavigation | null>(null);

export function ConceptNavigationProvider({
  navigation,
  children,
}: {
  navigation: ConceptNavigation;
  children: ReactNode;
}) {
  return (
    <ConceptNavigationContext.Provider value={navigation}>
      {children}
    </ConceptNavigationContext.Provider>
  );
}

/** Null outside the workbench, so a pill degrades to a label, not a dead button. */
export function useConceptNavigation(): ConceptNavigation | null {
  return useContext(ConceptNavigationContext);
}
