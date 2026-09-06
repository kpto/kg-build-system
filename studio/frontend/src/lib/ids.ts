/**
 * IR references: the stable address of anything editable, mirrored from
 * `studio_backend.ir.refs`.
 *
 * A reference is `<kind>:<id>` with an optional tail locating one part of it, e.g.
 * `component:site`, `component:site.property.summary`,
 * `binding:site_binding.property.summary`. Everything cross-cutting — diagnostics,
 * canvas positions, selection, anchor hits — speaks this form.
 */

import type { DocumentSection, ProjectDocument, RefKind } from "./ir";
import { SECTION_BY_KIND, findInSection } from "./ir";

const IDENTIFIER = "[a-z][a-z0-9_]*";
const KINDS =
  "table|struct|projection|component|binding|source|module|annotation_type";
const PATTERN = new RegExp(
  `^(?<kind>${KINDS}):(?<id>${IDENTIFIER})(?:\\.(?<part>[a-z_]+)(?:\\.(?<name>.+))?)?$`,
);

export interface Reference {
  readonly kind: RefKind;
  readonly id: string;
  readonly part: string | null;
  readonly name: string | null;
}

export class ReferenceError extends Error {}

/** `null` rather than a throw: refs arriving from the network may be malformed. */
export function parseRef(value: string | null | undefined): Reference | null {
  if (!value) return null;
  const match = PATTERN.exec(value);
  if (!match?.groups) return null;
  return {
    kind: match.groups["kind"] as RefKind,
    id: match.groups["id"] ?? "",
    part: match.groups["part"] ?? null,
    name: match.groups["name"] ?? null,
  };
}

export function buildRef(
  kind: RefKind,
  id: string,
  part?: string | null,
  name?: string | null,
): string {
  let tail = part ? `.${part}` : "";
  tail += name ? `.${name}` : "";
  return `${kind}:${id}${tail}`;
}

export function refSection(ref: string | null | undefined): DocumentSection | null {
  const parsed = parseRef(ref);
  return parsed ? SECTION_BY_KIND[parsed.kind] : null;
}

/** `component:site.property.summary` → `component:site`. */
export function entityRef(ref: string | null | undefined): string | null {
  const parsed = parseRef(ref);
  return parsed ? buildRef(parsed.kind, parsed.id) : null;
}

export function childRef(ref: string, part: string, name?: string | null): string {
  const parsed = parseRef(ref);
  if (!parsed) throw new ReferenceError(`malformed IR reference ${ref}`);
  return buildRef(parsed.kind, parsed.id, part, name ?? null);
}

/** The declared item a reference locates, or `null` when it dangles. */
export function resolveRef(document: ProjectDocument | null, ref: string | null | undefined) {
  const parsed = parseRef(ref);
  if (!document || !parsed) return null;
  return findInSection(document, SECTION_BY_KIND[parsed.kind], parsed.id);
}

/* ------------------------------------------------------------------ naming helpers */

/** Authoring ids are snake_case; names double as the generated declaration identity. */
export function slugId(label: string, fallback = "item"): string {
  const slug = label
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
  return /^[a-z]/.test(slug) ? slug : slug ? `_${slug}`.replace(/^_+/, "") : fallback;
}

/** `site` + `node` → `SiteNode`, matching the generator's naming rule. */
export function declarationName(id: string, suffix = ""): string {
  const words = id.split(/[^A-Za-z0-9]+/).filter(Boolean);
  const parts = words.map((word) => word.charAt(0).toUpperCase() + word.slice(1));
  if (suffix) {
    const tail = suffix.replace(/[^A-Za-z0-9]+/g, " ").trim().split(/\s+/);
    parts.push(...tail.map((word) => word.charAt(0).toUpperCase() + word.slice(1)));
  }
  return parts.join("") || "Item";
}

/** An id not present in `taken`, suffixed `_2`, `_3`, … */
export function freeId(desired: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  if (!used.has(desired)) return desired;
  for (let n = 2; n < 10_000; n += 1) {
    const candidate = `${desired}_${n}`;
    if (!used.has(candidate)) return candidate;
  }
  return `${desired}_${Date.now()}`;
}

/**
 * A short human label for a ref, used by titles, tooltips and the palette:
 * `component:site.property.summary` → `site · property summary`.
 */
export function refLabel(ref: string | null | undefined): string {
  const parsed = parseRef(ref);
  if (!parsed) return ref ?? "";
  if (parsed.part === null) return parsed.id;
  return parsed.name
    ? `${parsed.id} · ${parsed.part} ${parsed.name}`
    : `${parsed.id} · ${parsed.part}`;
}
