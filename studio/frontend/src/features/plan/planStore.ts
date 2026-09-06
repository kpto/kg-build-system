"use client";

/**
 * Plan store — the compiled DAG, cached outside React so switching tabs does not
 * refetch or re-layout.
 *
 * The plan is *not* document state and the shell does not hand it to features (see
 * `src/lib/types.ts::FeatureProps`), so this area owns the fetch: `GET /api/plan`
 * on first mount, `GET /api/plan?refresh=1` when the user asks for a recompile.
 * `?mock=1` has no backend to ask, and `src/lib/mock.ts` ships no plan fixture, so
 * mock mode loads the real captured plan in `samplePlan.json` instead.
 */

import { create } from "zustand";

import { api, ApiError } from "@/lib/api";
import { useConnectionStore } from "@/stores/connectionStore";
import type { PlanResponse, Problem } from "@/lib/types";
import type { StepEdge, StepNode, StepPlan } from "./types";
import { SAMPLE_PLAN } from "./samplePlan";

export interface PlanState {
  plan: StepPlan | null;
  nodes: readonly StepNode[];
  edges: readonly StepEdge[];
  errors: readonly Problem[];
  fingerprint: string | null;
  /** `mock` = the bundled real-plan capture; `live` = `GET /api/plan`. */
  source: "idle" | "mock" | "live" | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  /** Bumped by every successful load so the canvas can decide when to re-fit. */
  generation: number;

  load(mock: boolean): Promise<void>;
  refresh(): Promise<void>;
  reset(): void;
}

let inFlight: Promise<void> | null = null;

function adopt(response: PlanResponse, source: "mock" | "live"): Partial<PlanState> {
  const plan = (response.plan ?? null) as StepPlan | null;
  return {
    plan,
    nodes: plan?.nodes ?? [],
    edges: plan?.edges ?? [],
    errors: response.errors ?? [],
    fingerprint: response.fingerprint ?? plan?.fingerprint ?? null,
    source,
    error: null,
  };
}

export const usePlanStore = create<PlanState>((set, get) => ({
  plan: null,
  nodes: [],
  edges: [],
  errors: [],
  fingerprint: null,
  source: null,
  loading: false,
  refreshing: false,
  error: null,
  generation: 0,

  async load(mock) {
    if (get().plan && get().source === (mock ? "mock" : "live")) return;
    if (inFlight) return inFlight;
    set({ loading: true, error: null });
    inFlight = (async () => {
      try {
        const response: PlanResponse = mock
          ? {
              plan: SAMPLE_PLAN as unknown as PlanResponse["plan"],
              errors: [],
              fingerprint: SAMPLE_PLAN.fingerprint ?? null,
            }
          : await api.getPlan();
        set({ ...adopt(response, mock ? "mock" : "live"), loading: false, generation: get().generation + 1 });
      } catch (cause: unknown) {
        set({
          loading: false,
          error: cause instanceof ApiError ? cause.reason : String(cause),
        });
      } finally {
        inFlight = null;
      }
    })();
    return inFlight;
  },

  /** `?refresh=1` — the backend re-runs the compile pass before answering. */
  async refresh() {
    if (get().refreshing) return;
    if (get().source === "mock" || get().source === null) {
      set({ refreshing: true });
      await get().load(true);
      set({ refreshing: false });
      return;
    }
    set({ refreshing: true, error: null });
    try {
      const response = await api.getPlan(true);
      set({ ...adopt(response, "live"), refreshing: false, generation: get().generation + 1 });
      // The staleness banner reads the shell's status model, and the status only
      // returns to `clean` over the socket. Re-read it the same way the shell does
      // (the resync entry point) rather than pretending the banner cleared.
      const state = await api.getState().catch(() => null);
      if (state?.status) useConnectionStore.getState().setStatus(state.status);
    } catch (cause: unknown) {
      set({
        refreshing: false,
        error: cause instanceof ApiError ? cause.reason : String(cause),
      });
    }
  },

  reset() {
    set({
      plan: null,
      nodes: [],
      edges: [],
      errors: [],
      fingerprint: null,
      source: null,
      loading: false,
      refreshing: false,
      error: null,
    });
  },
}));

