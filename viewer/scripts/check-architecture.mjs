#!/usr/bin/env node
/**
 * Ownership and MVVM boundary check.
 *
 * Two hierarchies must stay coherent: the visible hierarchy (window, task,
 * panel, section, row, field) and the ViewModel hierarchy. This script guards
 * the code side of both.
 *
 * 1. A feature may import `shared/`, `lib/` and itself. Only the campaign
 *    composition root (`review/`) may import across features.
 * 2. A ViewModel (any file under a `model` directory) is framework agnostic:
 *    no React, no JSX, no DOM, no view import, no `build*` call to a view.
 * 3. A view never constructs its ViewModel: `build*Model` may only be called
 *    from the campaign composition root.
 * 4. The deleted `@/components` tree may not come back.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, sep } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const features = new Set([
  "review",
  "navigation",
  "properties",
  "diagnosis",
  "topology",
  "audit",
  "shared",
  "app",
]);
const allowed = {
  review: new Set([...features, "lib"]),
  app: new Set(["review", "shared", "lib"]),
  shared: new Set(["shared", "lib"]),
  navigation: new Set(["navigation", "shared", "lib"]),
  properties: new Set(["properties", "shared", "lib"]),
  diagnosis: new Set(["diagnosis", "shared", "lib"]),
  topology: new Set(["topology", "shared", "lib"]),
  audit: new Set(["audit", "shared", "lib"]),
};

/** The only module allowed to assemble the model tree, and thus call builders. */
const COMPOSITION_ROOT = "review";

function walk(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) out.push(...walk(path));
    else if (/\.(ts|tsx)$/.test(path)) out.push(path);
  }
  return out;
}

const isModel = (file) => {
  const parts = relative(root, file).split(sep);
  return parts.includes("model");
};

/** Feature directories whose React files must sit in a view zone. */
const VIEW_ZONES = new Set(["view", "binding", "tasks"]);
const FEATURE_DIRS = new Set([
  "review",
  "navigation",
  "properties",
  "topology",
  "diagnosis",
  "audit",
]);
/** The feature entry wrapper is a view by another name; keep it at the root. */
const ENTRY_FILES = new Set([
  "detail/DetailFeature.tsx",
  "topology/TopologyFeature.tsx",
]);

const zoneOf = (file) => {
  const parts = relative(root, file).split(sep);
  return parts.find((part) => VIEW_ZONES.has(part));
};

const errors = [];

for (const feature of Object.keys(allowed)) {
  const dir = join(root, feature);
  let files;
  try {
    files = walk(dir);
  } catch {
    continue;
  }
  for (const file of files) {
    const source = readFileSync(file, "utf8");
    const name = relative(root, file);

    // 1. Ownership boundary.
    for (const match of source.matchAll(/from\s+["']@\/([^"']+)["']/g)) {
      const target = match[1].split("/")[0];
      if (target === "components") {
        errors.push(`${name} imports the deleted @/components tree`);
        continue;
      }
      if (!features.has(target) && target !== "lib") continue;
      if (!allowed[feature].has(target)) {
        errors.push(`${name} (${feature}) imports @/${match[1]} (${target})`);
      }
    }

    // 2. A ViewModel is framework agnostic.
    if (isModel(file)) {
      if (/from\s+["']react["']/.test(source)) {
        errors.push(`${name} is a ViewModel and must not import React`);
      }
      if (/^\s*["']use client["']/m.test(source)) {
        errors.push(`${name} is a ViewModel and must not be a client component`);
      }
      if (/from\s+["']@\/[^"']*\/view\//.test(source)) {
        errors.push(`${name} is a ViewModel and must not import a view`);
      }
      if (/\.tsx["']/.test(source)) {
        errors.push(`${name} is a ViewModel and must not import a .tsx module`);
      }
      if (/return\s*\(\s*</.test(source) || /=>\s*\(\s*</.test(source)) {
        errors.push(`${name} is a ViewModel and must not contain JSX`);
      }
    }

    // 3. A feature's React files live in a view zone.
    if (
      FEATURE_DIRS.has(feature) &&
      file.endsWith(".tsx") &&
      !isModel(file) &&
      !zoneOf(file) &&
      !ENTRY_FILES.has(name)
    ) {
      errors.push(
        `${name} is a feature React file outside view/, binding/ or tasks/`,
      );
    }

    // 4. Only the composition root builds ViewModels.
    if (feature !== COMPOSITION_ROOT && !isModel(file)) {
      for (const match of source.matchAll(/\b(build[A-Z]\w*Model)\s*\(/g)) {
        errors.push(
          `${name} calls ${match[1]}(); models are built by the ${COMPOSITION_ROOT} composition root`,
        );
      }
    }
  }
}

if (errors.length) {
  console.error("Ownership boundary violations:\n" + errors.join("\n"));
  process.exit(1);
}
console.log("Ownership boundaries OK");
