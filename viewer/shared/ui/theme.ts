/**
 * Shared visual tokens for JavaScript-side styling.
 *
 * CSS owns the values in `app/globals.css`; components import these names so a
 * React Flow edge, an SVG map or a chart never invents a local palette. Use the
 * same names in Tailwind (`bg-panel`, `text-muted`, `border-line`) where a class
 * works.
 */

export const theme = {
  page: "var(--color-abyss)",
  panel: "var(--color-panel)",
  raised: "var(--color-panel-raised)",
  soft: "var(--color-panel-soft)",
  line: "var(--color-line)",
  lineSoft: "var(--color-line-soft)",
  edge: "var(--color-edge)",
  edgeStrong: "var(--color-edge-strong)",
  lineStrong: "var(--color-line-strong)",
  text: "var(--color-text)",
  ink: "var(--color-ink)",
  inkSoft: "var(--color-ink-soft)",
  muted: "var(--color-muted)",
  faint: "var(--color-faint)",
  accent: "var(--color-accent)",
  accentStrong: "var(--color-accent-strong)",
  accentSoft: "var(--color-accent-soft)",
  accentInk: "var(--color-accent-ink)",
  onAccent: "var(--color-on-accent)",
  selection: "var(--color-selection)",
  selectionStrong: "var(--color-selection-strong)",
  selectionSoft: "var(--color-selection-soft)",
  secondary: "var(--color-secondary)",
  secondarySoft: "var(--color-secondary-soft)",
  asset: "var(--color-asset)",
  source: "var(--color-source)",
  transform: "var(--color-transform)",
  binding: "var(--color-binding)",
  post: "var(--color-post)",
  target: "var(--color-target)",
  critical: "var(--color-critical)",
  high: "var(--color-high)",
  medium: "var(--color-medium)",
  low: "var(--color-low)",
  info: "var(--color-info)",
  group7: "var(--color-group-7)",
  group8: "var(--color-group-8)",
  group9: "var(--color-group-9)",
  group10: "var(--color-group-10)",
} as const;

export const severityColor = {
  critical: theme.critical,
  high: theme.high,
  medium: theme.medium,
  low: theme.low,
  info: theme.info,
} as const;

export const laneColor = {
  asset: theme.asset,
  source: theme.source,
  transformation: theme.transform,
  binding: theme.binding,
  post: theme.post,
  target: theme.target,
} as const;

/** Stable group colors for maps and grouped cards. */
export const groupPalette = [
  theme.asset,
  theme.source,
  theme.transform,
  theme.binding,
  theme.post,
  theme.target,
  theme.group7,
  theme.group8,
  theme.group9,
  theme.group10,
] as const;

/** Small class-name joiner; avoid adding a dependency for this. */
export function cx(
  ...values: Array<string | false | null | undefined>
): string {
  return values.filter(Boolean).join(" ");
}
