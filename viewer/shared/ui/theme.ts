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
  conceptGraph: "var(--color-concept-graph)",
  conceptAbstract: "var(--color-concept-abstract)",
  conceptNode: "var(--color-concept-node)",
  conceptEdge: "var(--color-concept-edge)",
  conceptProperty: "var(--color-concept-property)",
  conceptAsset: "var(--color-concept-asset)",
  conceptSource: "var(--color-concept-source)",
  conceptDerived: "var(--color-concept-derived)",
  conceptField: "var(--color-concept-field)",
  conceptBinding: "var(--color-concept-binding)",
  conceptWorkflow: "var(--color-concept-workflow)",
  conceptStep: "var(--color-concept-step)",
  conceptMeaning: "var(--color-concept-meaning)",
  lineDeep: "var(--color-line-deep)",
  rowHover: "var(--color-row-hover)",
  rowActive: "var(--color-row-active)",
  overlay: "var(--color-overlay)",
  scrim: "var(--color-scrim)",
  grid: "var(--color-grid)",
  glow: "var(--color-glow)",
} as const;

/** The literal page colour for metadata that cannot read a CSS variable. */
export const themeColor = "#1d1d1d";

/** Type roles, not measurements; use a role rather than a local size. */
export const type = {
  micro: "var(--text-micro)",
  caption: "var(--text-caption)",
  body: "var(--text-body)",
  label: "var(--text-label)",
  title: "var(--text-title)",
  heading: "var(--text-heading)",
  display: "var(--text-display)",
} as const;

/** The one spacing scale for gaps, padding and margins. */
export const space = {
  hairline: "var(--space-hairline)",
  inline: "var(--space-inline)",
  stack: "var(--space-stack)",
  group: "var(--space-group)",
  section: "var(--space-section)",
  panel: "var(--space-panel)",
  region: "var(--space-region)",
  page: "var(--space-page)",
} as const;

export const border = {
  hairline: "var(--border-hairline)",
  heavy: "var(--border-heavy)",
} as const;

export const radius = {
  sm: "var(--radius-sm)",
  md: "var(--radius-md)",
  pill: "var(--radius-pill)",
} as const;

export const shadow = {
  popover: "var(--shadow-popover)",
  panel: "var(--shadow-panel)",
  modal: "var(--shadow-modal)",
  inset: "var(--shadow-inset)",
  selection: "var(--shadow-selection)",
  railAccent: "var(--shadow-rail-accent)",
  railSelection: "var(--shadow-rail-selection)",
} as const;

export const motion = {
  fast: "var(--motion-fast)",
  base: "var(--motion-base)",
  slow: "var(--motion-slow)",
  pulse: "var(--motion-pulse)",
  none: "var(--motion-none)",
  instrument: "var(--ease-instrument)",
  standard: "var(--ease-standard)",
  out: "var(--ease-out)",
  inOut: "var(--ease-in-out)",
} as const;

export const z = {
  raised: "var(--z-raised)",
  sticky: "var(--z-sticky)",
  overlay: "var(--z-overlay)",
  modal: "var(--z-modal)",
  tooltip: "var(--z-tooltip)",
  top: "var(--z-top)",
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
