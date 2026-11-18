#!/usr/bin/env node
/**
 * Theme contract check.
 *
 * A component reads the shared design language in `app/globals.css` and
 * `shared/ui/theme.ts`; it does not invent a colour, type size, radius, shadow,
 * spacing step, weight, tracking, layer or motion duration.
 *
 * Local geometry (widths, heights, grid templates, breakpoints) stays in the
 * component because it describes that component's composition, not the system.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const SOURCE_DIRS = [
  "app",
  "detail",
  "shared",
  "topology",
  "workflow",
  "workbench",
];
const SKIP = new Set(["node_modules", ".next", "out"]);

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    if (SKIP.has(entry)) continue;
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) out.push(...walk(path));
    else out.push(path);
  }
  return out;
}

const errors = [];
const css = [];
const tsx = [];
for (const dir of SOURCE_DIRS) {
  let files;
  try {
    files = walk(join(root, dir));
  } catch {
    continue;
  }
  for (const file of files) {
    if (file.endsWith(".module.css")) css.push(file);
    if (file.endsWith(".tsx")) tsx.push(file);
  }
}
css.push(join(root, "app/globals.css"));

const rawColor = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/;
const spacing = /(?:gap|row-gap|column-gap|padding|margin)[a-z-]*\s*:[^;]*[1-9][0-9]*px/;
const typeSize = /font-size:\s*[0-9.]+px/;
const radius = /border-radius:\s*[0-9.]+px/;
const tracking = /letter-spacing:\s*-?[0-9.]+em/;
const weight = /font-weight:\s*[0-9]+/;
const leading = /line-height:\s*[0-9.]+/;
const layer = /z-index:\s*-?[0-9]+/;
const duration = /(?:transition|animation)[a-z-]*\s*:[^;]*\b[0-9]+(?:\.[0-9]+)?m?s\b/;
const borderWidth = /(?:border(?:-(?:top|right|bottom|left))?(?:-width)?|outline(?:-width)?):\s*[0-9]+px/;
const fontFamily = /font-family:\s*(?!\s*var\()/;

for (const file of css) {
  const name = relative(root, file);
  const source = readFileSync(file, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  for (const [index, line] of source.split("\n").entries()) {
    if (/--space-[0-9]/.test(line)) {
      errors.push(
        `${name}:${index + 1}: a numbered spacing token; use a spacing role\n  ${line.trim()}`,
      );
    }
    if (/^\s*--[a-z0-9-]+\s*:/.test(line)) continue;
    const checks = [
      [rawColor, "a raw colour; use a --color-* token"],
      [spacing, "a raw spacing value; use a spacing role"],
      [typeSize, "a raw font size; use a --text-* token"],
      [radius, "a raw radius; use a --radius-* token"],
      [tracking, "a raw tracking value; use a --tracking-* token"],
      [weight, "a raw font weight; use a --weight-* token"],
      [leading, "a raw line height; use a --leading-* token"],
      [layer, "a raw z-index; use a --z-* token"],
      [duration, "a raw motion duration; use a --motion-* token"],
      [borderWidth, "a raw border width; use a --border-* token"],
      [fontFamily, "a raw font family; use a --font-* token"],
    ];
    for (const [pattern, message] of checks) {
      if (pattern.test(line)) {
        errors.push(`${name}:${index + 1}: ${message}\n  ${line.trim()}`);
      }
    }
  }
}

for (const file of tsx) {
  const name = relative(root, file);
  const source = readFileSync(file, "utf8");
  for (const [index, line] of source.split("\n").entries()) {
    if (rawColor.test(line)) {
      errors.push(`${name}:${index + 1}: a raw colour; use the theme token\n  ${line.trim()}`);
    }
    if (/text-\[[0-9.]+px\]/.test(line)) {
      errors.push(
        `${name}:${index + 1}: a raw text size; use the text length token\n  ${line.trim()}`,
      );
    }
  }
}

if (errors.length) {
  console.error(`Theme contract violations:\n${errors.join("\n")}`);
  process.exit(1);
}
console.log("Theme contract OK");
