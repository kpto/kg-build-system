/**
 * Authoring index store: `/api/index` cached, keyed by document revision.
 *
 * The index is derived from the document, so every accepted write invalidates it.
 * `onRevisionChange` is called by the shell after an acknowledged edit or a remote
 * document event; refreshes are coalesced because a burst of edits must not cause a
 * burst of index requests.
 */

import { create } from "zustand";

import { api } from "@/lib/api";
import type { AuthoringIndex, OperatorEntry, SelectableEntry } from "@/lib/types";

export interface IndexState {
  index: AuthoringIndex | null;
  /** The document revision the cached index was computed from. */
  forRevision: number | null;
  loading: boolean;
  error: string | null;

  refresh(): Promise<void>;
  /** Refresh only when the cached index describes a different revision. */
  onRevisionChange(revision: number): void;
  hydrate(index: AuthoringIndex, revision: number): void;
  /** Forget the cache without failing UI that already read it. */
  invalidate(): void;
  reset(): void;
}

let inflight: Promise<void> | null = null;
let debounce: ReturnType<typeof setTimeout> | null = null;

export const useIndexStore = create<IndexState>((set, get) => ({
  index: null,
  forRevision: null,
  loading: false,
  error: null,

  async refresh() {
    if (inflight) return inflight;
    set({ loading: true });
    inflight = api
      .getIndex()
      .then((index) => set({ index, loading: false, error: null, forRevision: get().forRevision }))
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

  onRevisionChange(revision) {
    if (get().forRevision === revision) return;
    if (debounce) clearTimeout(debounce);
    debounce = setTimeout(() => {
      debounce = null;
      void get().refresh();
    }, 120);
  },

  hydrate(index, revision) {
    set({ index, forRevision: revision, loading: false, error: null });
  },

  invalidate() {
    set({ forRevision: null });
  },

  reset() {
    if (debounce) {
      clearTimeout(debounce);
      debounce = null;
    }
    set({ index: null, forRevision: null, loading: false, error: null });
  },
}));

export const selectSelectable = (state: IndexState): readonly SelectableEntry[] =>
  state.index?.selectable ?? [];

export const selectOperators = (state: IndexState): readonly OperatorEntry[] =>
  state.index?.operators ?? [];
