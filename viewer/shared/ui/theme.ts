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
  lineMid: "var(--color-line-mid)",
  panelShade: "var(--color-panel-shade)",
  panelDeep: "var(--color-panel-deep)",
  panelMuted: "var(--color-panel-muted)",
  rowHover: "var(--color-row-hover)",
  rowActive: "var(--color-row-active)",
  onActive: "var(--color-on-active)",
  onActiveMuted: "var(--color-on-active-muted)",
  criticalStrong: "var(--color-critical-strong)",
  selectionBorder: "var(--color-selection-border)",
  selectionInk: "var(--color-selection-ink)",
  overlay: "var(--color-overlay)",
  overlayStrong: "var(--color-overlay-strong)",
  scrim: "var(--color-scrim)",
  grid: "var(--color-grid)",
  gridStrong: "var(--color-grid-strong)",
  glow: "var(--color-glow)",
} as const;

/** The literal page colour for metadata that cannot read a CSS variable. */
export const themeColor = "#1d1d1d";

/** Type scale; use a token name rather than a local pixel value. */
export const type = {
  "3xs": "var(--text-3xs)",
  "2xs": "var(--text-2xs)",
  xs: "var(--text-xs)",
  sm: "var(--text-sm)",
  md: "var(--text-md)",
  base: "var(--text-base)",
  lg: "var(--text-lg)",
  xl: "var(--text-xl)",
  "2xl": "var(--text-2xl)",
  "3xl": "var(--text-3xl)",
  root: "var(--text-root)",
  "4xl": "var(--text-4xl)",
  "5xl": "var(--text-5xl)",
  "6xl": "var(--text-6xl)",
  "7xl": "var(--text-7xl)",
  "8xl": "var(--text-8xl)",
} as const;

/** The one spacing scale for gaps, padding and margins. */
export const space = {
  1: "var(--space-1)",
  2: "var(--space-2)",
  3: "var(--space-3)",
  4: "var(--space-4)",
  5: "var(--space-5)",
  6: "var(--space-6)",
  7: "var(--space-7)",
  8: "var(--space-8)",
  9: "var(--space-9)",
  10: "var(--space-10)",
  11: "var(--space-11)",
  12: "var(--space-12)",
  13: "var(--space-13)",
  14: "var(--space-14)",
  15: "var(--space-15)",
  16: "var(--space-16)",
  17: "var(--space-17)",
  18: "var(--space-18)",
  20: "var(--space-20)",
  24: "var(--space-24)",
  26: "var(--space-26)",
  28: "var(--space-28)",
  32: "var(--space-32)",
  36: "var(--space-36)",
} as const;

export const border = {
  hairline: "var(--border-hairline)",
  heavy: "var(--border-heavy)",
} as const;

export const radius = {
  none: "var(--radius-none)",
  sm: "var(--radius-sm)",
  md: "var(--radius-md)",
  lg: "var(--radius-lg)",
  xl: "var(--radius-xl)",
  pill: "var(--radius-pill)",
} as const;

export const shadow = {
  popover: "var(--shadow-popover)",
  popoverStrong: "var(--shadow-popover-strong)",
  panel: "var(--shadow-panel)",
  modal: "var(--shadow-modal)",
  inset: "var(--shadow-inset)",
  selection: "var(--shadow-selection)",
  railAccent: "var(--shadow-rail-accent)",
  railSelection: "var(--shadow-rail-selection)",
} as const;

export const motion = {
  fast: "var(--motion-fast)",
  snap: "var(--motion-snap)",
  quick: "var(--motion-quick)",
  base: "var(--motion-base)",
  slow: "var(--motion-slow)",
  long: "var(--motion-long)",
  none: "var(--motion-none)",
  instrument: "var(--ease-instrument)",
  standard: "var(--ease-standard)",
  out: "var(--ease-out)",
  inOut: "var(--ease-in-out)",
} as const;

export const z = {
  raised: "var(--z-raised)",
  sticky: "var(--z-sticky)",
  header: "var(--z-header)",
  overlay: "var(--z-overlay)",
  modal: "var(--z-modal)",
  tooltip: "var(--z-tooltip)",
  top: "var(--z-top)",
  grain: "var(--z-grain)",
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
