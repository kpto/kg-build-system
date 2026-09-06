/**
 * Catalogue store: `/api/catalog` cached once.
 *
 * The catalogue is what the framework exposes (configured modules, the canonical
 * unit vocabulary, the operator list) and only changes when the backend is
 * restarted, so it is fetched once and refreshed by hand.
 */

import { create } from "zustand";

import { api } from "@/lib/api";
import type { CatalogResponse, ModuleEntry } from "@/lib/types";

export interface CatalogState {
  catalog: CatalogResponse | null;
  loading: boolean;
  error: string | null;
  fetchedAt: number | null;

  refresh(): Promise<void>;
  hydrate(catalog: CatalogResponse): void;
  reset(): void;
}

let inflight: Promise<void> | null = null;

export const useCatalogStore = create<CatalogState>((set) => ({
  catalog: null,
  loading: false,
  error: null,
  fetchedAt: null,

  async refresh() {
    // Two panels mounting at once must not cause two round trips.
    if (inflight) return inflight;
    set({ loading: true, error: null });
    inflight = api
      .getCatalog()
      .then((catalog) => set({ catalog, loading: false, fetchedAt: Date.now() }))
      .catch((error: unknown) => {
        set({
          loading: false,
          error: error instanceof Error ? error.message : String(error),
        });
      })
      .finally(() => {
        inflight = null;
      });
    return inflight;
  },

  hydrate(catalog) {
    set({ catalog, loading: false, error: null, fetchedAt: Date.now() });
  },

  reset() {
    set({ catalog: null, loading: false, error: null, fetchedAt: null });
  },
}));

export const selectModules = (state: CatalogState): readonly ModuleEntry[] =>
  state.catalog?.modules ?? [];

export const selectUnitNames = (state: CatalogState): string[] =>
  (state.catalog?.units ?? []).map((item) => item.name);
