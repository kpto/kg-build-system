/**
 * The spacing slider's mapping to layout gaps.
 *
 * Kept out of the component so the control's effect on the layout is testable
 * without a canvas: one 0–100 value drives both gaps (the strip's single "spacing"
 * control), and the clamping stops a rogue value producing a degenerate layout.
 */

import type { LayoutSpacing } from "./types";

export const MIN_SPACING: LayoutSpacing = { columnGap: 48, rowGap: 12 };
export const SPACING_RANGE: LayoutSpacing = { columnGap: 176, rowGap: 68 };

export function spacingFor(value: number): LayoutSpacing {
  const clamped = Math.min(100, Math.max(0, Number.isFinite(value) ? value : 50));
  const t = clamped / 100;
  return {
    columnGap: Math.round(MIN_SPACING.columnGap + t * SPACING_RANGE.columnGap),
    rowGap: Math.round(MIN_SPACING.rowGap + t * SPACING_RANGE.rowGap),
  };
}
