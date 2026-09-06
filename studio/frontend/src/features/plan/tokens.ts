/**
 * The literal token values from `src/app/globals.css`.
 *
 * Edge strokes and arrowhead fills are SVG *attributes*, and `var(…)` does not
 * resolve there, so the canvas needs the hex values. They are kept next to the
 * token names they mirror so a token change is a one-line change here.
 */

export const TOKEN = {
  canvas: "#0a0c11",
  surface: "#10141c",
  raised: "#161c26",
  overlay: "#1c2430",
  line: "#232c3a",
  lineStrong: "#35435a",
  ink: "#e6e9ef",
  muted: "#8c98ab",
  faint: "#5c6779",
  node: "#4c8dff",
  nodeSoft: "#1b2a45",
  category: "#8494ab",
  relation: "#35c98d",
  relationSoft: "#12312a",
  edgekind: "#b57bff",
  template: "#d8a657",
  danger: "#ff6b6b",
  warn: "#ffb547",
  ok: "#35c98d",
  info: "#4c8dff",
} as const;
