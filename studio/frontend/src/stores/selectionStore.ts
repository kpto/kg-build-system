/**
 * Selection store.
 *
 * `selectedRef` is global — the inspector, the problems panel and every feature
 * area follow it. Each tab additionally keeps its own local selection (which row of
 * a table is open, which canvas node is focused) so switching tabs and coming back
 * does not lose the user's place, and so a feature's internal cursor never leaks
 * into another area.
 */

import { create } from "zustand";

import { parseRef } from "@/lib/ids";
import { AREA_FOR_REF_KIND, type TabArea } from "@/lib/types";

export interface SelectionState {
  selectedRef: string | null;
  /** The tab the shell is showing. */
  area: TabArea;
  /** Per-tab local selection, keyed by tab id. */
  local: Partial<Record<TabArea, string | null>>;
  /** True while the shell should scroll/center the selection into view. */
  revealToken: number;
  /**
   * A one-shot request for a tab to open a flow it owns. Jumping to a tab with no
   * selection must not let that tab fall back to an arbitrary row and imply the row
   * was what the user asked for; the intent says what they actually asked for.
   */
  pendingIntent: FeatureIntent | null;

  select(ref: string | null): void;
  /** Select and jump to the area that owns the ref (problem click, palette). */
  selectAndReveal(ref: string | null): TabArea | null;
  setArea(area: TabArea): void;
  localSelection(area: TabArea): string | null;
  setLocalSelection(area: TabArea, ref: string | null): void;
  /** Ask `area` to start `kind`, carrying whatever the caller knows. */
  requestIntent(area: TabArea, kind: FeatureIntentKind, seed?: Record<string, string>): void;
  /** Read and clear the intent if it belongs to `area`; otherwise `null`. */
  takeIntent(area: TabArea): FeatureIntent | null;
  reset(): void;
}

export type FeatureIntentKind = "new-binding";

export interface FeatureIntent {
  readonly area: TabArea;
  readonly kind: FeatureIntentKind;
  readonly seed: Record<string, string>;
}

/** The area that owns a ref, or `null` when the ref is unknown/unqualified. */
export function areaForRef(ref: string | null | undefined): TabArea | null {
  const parsed = parseRef(ref);
  return parsed ? (AREA_FOR_REF_KIND[parsed.kind] ?? null) : null;
}

export const useSelectionStore = create<SelectionState>((set, get) => ({
  selectedRef: null,
  area: "topology",
  local: {},
  revealToken: 0,
  pendingIntent: null,

  select(ref) {
    // The exact ref is kept: selecting `table:sites.field.site_id` must address the
    // field, not collapse onto the table.
    set({ selectedRef: ref && parseRef(ref) ? ref : null });
  },

  selectAndReveal(ref) {
    const parsed = parseRef(ref);
    const area = areaForRef(ref);
    set((state) => ({
      selectedRef: parsed ? ref : null,
      area: area ?? state.area,
      revealToken: state.revealToken + 1,
    }));
    return area;
  },

  setArea(area) {
    set({ area });
  },

  localSelection(area) {
    return get().local[area] ?? null;
  },

  setLocalSelection(area, ref) {
    set((state) => ({ local: { ...state.local, [area]: ref } }));
  },

  requestIntent(area, kind, seed = {}) {
    set({ pendingIntent: { area, kind, seed } });
  },

  takeIntent(area) {
    const intent = get().pendingIntent;
    if (!intent || intent.area !== area) return null;
    set({ pendingIntent: null });
    return intent;
  },

  reset() {
    set({ selectedRef: null, area: "topology", local: {}, pendingIntent: null });
  },
}));

export const selectSelectedRef = (state: SelectionState): string | null => state.selectedRef;
export const selectArea = (state: SelectionState): TabArea => state.area;
