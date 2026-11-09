/**
 * Deep-link state for the viewer.
 *
 * Known parameters are parsed into typed state; every other parameter is kept
 * verbatim so a link can carry an embed flag, a debug switch or another app's
 * state. Writes use `history.replaceState`, never navigation.
 */

import type { StepId } from "./types";

export type ReviewView =
  | "map"
  | "workflow"
  | "blueprint"
  | "lineage"
  | "review";

export interface ReviewUrlState {
  view: ReviewView;
  kind?: "node" | "edge";
  component?: string;
  property?: string;
  /** Relation filter for a coverage-matrix cell. */
  source?: string;
  step?: StepId;
  finding?: string;
  /** Query parameters this module does not own, preserved across round trips. */
  params?: Record<string, string>;
}

const VIEWS: ReviewView[] = [
  "map",
  "workflow",
  "blueprint",
  "lineage",
  "review",
];
const KINDS = ["node", "edge"] as const;
const KNOWN_PARAMS = new Set([
  "view",
  "kind",
  "component",
  "property",
  "source",
  "step",
  "finding",
]);

function isView(value: string | null): value is ReviewView {
  return value !== null && (VIEWS as string[]).includes(value);
}

function isKind(value: string | null): value is "node" | "edge" {
  return value !== null && (KINDS as readonly string[]).includes(value);
}

export function parseReviewUrlState(search: string): ReviewUrlState {
  const params = new URLSearchParams(
    search.startsWith("?") ? search.slice(1) : search,
  );
  const viewValue = params.get("view");
  const state: ReviewUrlState = {
    view: isView(viewValue) ? viewValue : "map",
    params: {},
  };

  const kind = params.get("kind");
  if (isKind(kind)) state.kind = kind;
  const component = params.get("component");
  if (component) state.component = component;
  const property = params.get("property");
  if (property) state.property = property;
  const source = params.get("source");
  if (source) state.source = source;
  const finding = params.get("finding");
  if (finding) state.finding = finding;

  const step = params.get("step");
  if (step) {
    const comma = step.indexOf(",");
    if (comma >= 0) {
      state.step = [step.slice(0, comma), step.slice(comma + 1)];
    }
  }

  const extras: Record<string, string> = {};
  params.forEach((value, key) => {
    if (!KNOWN_PARAMS.has(key)) extras[key] = value;
  });
  state.params = extras;

  return state;
}

export function formatReviewUrlState(state: ReviewUrlState): string {
  const params = new URLSearchParams();
  params.set("view", state.view);
  if (state.kind) params.set("kind", state.kind);
  if (state.component) params.set("component", state.component);
  if (state.property) params.set("property", state.property);
  if (state.source) params.set("source", state.source);
  if (state.step) params.set("step", `${state.step[0]},${state.step[1]}`);
  if (state.finding) params.set("finding", state.finding);
  for (const [key, value] of Object.entries(state.params ?? {})) {
    if (!KNOWN_PARAMS.has(key) && value) params.set(key, value);
  }
  return params.toString();
}

export function readUrlState(): ReviewUrlState {
  if (typeof window === "undefined") {
    return { view: "map", params: {} };
  }
  return parseReviewUrlState(window.location.search);
}

export function writeUrlState(state: ReviewUrlState): void {
  if (typeof window === "undefined") return;
  // Unknown parameters already on the URL survive a write even when the caller
  // only passes typed state.
  const current = parseReviewUrlState(window.location.search);
  const merged: ReviewUrlState = {
    ...state,
    params: { ...current.params, ...(state.params ?? {}) },
  };
  const search = formatReviewUrlState(merged);
  const location = window.location;
  const next = `${location.pathname}${search ? `?${search}` : ""}${location.hash}`;
  window.history?.replaceState?.(null, "", next);
}
