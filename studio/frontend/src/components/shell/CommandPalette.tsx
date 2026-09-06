"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import clsx from "clsx";

import { SearchIcon } from "@/components/ui";
import { buildRef, parseRef, refLabel } from "@/lib/ids";
import { documentEntities, typeLabel } from "@/lib/ir";
import type { ProjectDocument } from "@/lib/ir";
import type { Problem } from "@/lib/types";
import { refSection } from "@/lib/ids";
import { findInSection, sectionItems } from "@/lib/ir";
import { useSelectionStore } from "@/stores/selectionStore";

export interface CommandPaletteProps {
  open: boolean;
  query: string;
  onQueryChange(value: string): void;
  document: ProjectDocument;
  problems: Problem[];
  onClose(): void;
}

interface Row {
  readonly ref: string;
  readonly label: string;
  readonly kind: string;
  readonly detail: string;
  readonly score: number;
}

/**
 * The global command palette: every IR entity by name, plus the typed parts inside
 * it (fields, property slots, filled slots), so `/` finds `city` as a component slot
 * and as a table field and takes you to whichever you pick.
 *
 * Filtering is a subsequence match with a prefix bonus — the behaviour users expect
 * from `cmd-p`, without a fuzzy-matching dependency.
 */
export function CommandPalette({
  open,
  query,
  onQueryChange,
  document,
  problems,
  onClose,
}: CommandPaletteProps) {
  const [index, setIndex] = useState(0);
  const listRef = useRef<HTMLDivElement | null>(null);
  const selectAndReveal = useSelectionStore((state) => state.selectAndReveal);

  const rows = useMemo(() => buildRows(document, query, problems), [document, query, problems]);

  useEffect(() => setIndex(0), [query]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        setIndex((value) => Math.min(value + 1, Math.max(0, rows.length - 1)));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setIndex((value) => Math.max(0, value - 1));
      } else if (event.key === "Enter") {
        event.preventDefault();
        const row = rows[index];
        if (row) {
          selectAndReveal(row.ref);
          onClose();
        }
      }
    };
    // Capture phase, so the shell's global key map never sees the palette's keys.
    window.addEventListener("keydown", onKey, true);
    return () => {
      window.removeEventListener("keydown", onKey, true);
    };
  }, [open, rows, index, onClose, selectAndReveal]);

  useEffect(() => {
    const node = listRef.current?.querySelector<HTMLElement>(`[data-row="${index}"]`);
    node?.scrollIntoView({ block: "nearest" });
  }, [index]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-canvas/70 pt-[14vh]"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search IR entities"
        className="studio-card flex max-h-[52vh] w-full max-w-2xl flex-col overflow-hidden"
      >
        <div className="flex h-10 shrink-0 items-center gap-2 border-b border-edge px-3">
          <SearchIcon size={15} className="text-faint" />
          <input
            autoFocus
            aria-label="Find IR entities"
            role="combobox"
            aria-expanded="true"
            aria-controls="palette-results"
            placeholder="name, kind or ref…"
            autoComplete="off"
            spellCheck={false}
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-[13px] text-ink outline-none placeholder:text-faint"
          />
          <kbd className="rounded border border-edge bg-raised px-1 font-mono text-[9px] text-faint">
            esc
          </kbd>
        </div>
        <div id="palette-results" ref={listRef} role="listbox" aria-label="Entities" className="min-h-0 flex-1 overflow-auto">
          {rows.length === 0 ? (
            <p className="p-4 text-center text-[12px] text-muted">
              Nothing in the document matches {query ? `“${query}”` : "this"}.
            </p>
          ) : (
            rows.slice(0, 200).map((row, position) => (
              <button
                key={`${row.ref}#${position}`}
                type="button"
                data-row={position}
                role="option"
                aria-selected={position === index}
                onMouseEnter={() => setIndex(position)}
                onClick={() => {
                  selectAndReveal(row.ref);
                  onClose();
                }}
                className={clsx(
                  "flex w-full items-center gap-2.5 px-3 py-1.5 text-left",
                  position === index ? "bg-raised" : "hover:bg-raised/60",
                )}
              >
                <span className="w-24 shrink-0 truncate text-[12px] text-ink">{row.label}</span>
                <span className="w-28 shrink-0 truncate font-mono text-[10px] uppercase text-faint">
                  {row.kind}
                </span>
                <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-muted">
                  {row.detail}
                </span>
                <span className="shrink-0 font-mono text-[10px] text-faint">{refLabel(row.ref)}</span>
              </button>
            ))
          )}
        </div>
        <footer className="flex h-7 shrink-0 items-center gap-3 border-t border-edge px-3 font-mono text-[10px] text-faint">
          <span>{rows.length} matches</span>
          <span>↑↓ select</span>
          <span>↵ open</span>
        </footer>
      </div>
    </div>
  );
}

/**
 * Word-wise subsequence match with a prefix bonus; `null` when nothing matches.
 *
 * Matching stops at a word boundary unless the query is still advancing, so `city`
 * finds `site_cities` and `priority…city` but never a word that merely happens to
 * contain the letters in order across several words.
 */
function score(needle: string, haystack: string): number | null {
  if (!needle) return 0;
  const text = haystack.toLowerCase();
  const query = needle.toLowerCase().trim();
  if (!query) return 0;

  const words = text.split(/[^a-z0-9]+/).filter(Boolean);
  let total = 0;
  let word = 0;
  for (const character of query) {
    if (character === " ") continue;
    let found = false;
    while (word < words.length) {
      const current = words[word] ?? "";
      const at = current.indexOf(character);
      if (at >= 0) {
        total += at === 0 ? 5 : 1;
        // Consume the rest of this word for the next character, then move on.
        words[word] = current.slice(at + 1);
        if (words[word]?.length === 0) word += 1;
        found = true;
        break;
      }
      word += 1;
    }
    if (!found) return null;
  }
  return total + (text.startsWith(query) ? 8 : 0);
}

function buildRows(document: ProjectDocument, query: string, problems: Problem[]): Row[] {
  const problemRefs = new Map<string, number>();
  for (const problem of problems) {
    if (problem.ref) problemRefs.set(problem.ref, (problemRefs.get(problem.ref) ?? 0) + 1);
  }

  const candidates: { ref: string; label: string; kind: string; detail: string }[] = [
    ...documentEntities(document),
    ...partEntities(document),
  ];

  const rows: Row[] = [];
  for (const candidate of candidates) {
    // Score the name and the ref separately: matching the concatenation lets a query
    // leap between fields and surface unrelated entities.
    const value =
      Math.max(score(query, candidate.label) ?? -Infinity, score(query, candidate.ref) ?? -Infinity) +
      (problemRefs.get(candidate.ref) ? 3 : 0);
    if (!Number.isFinite(value)) continue;
    rows.push({ ...candidate, score: value });
  }
  return rows.sort((a, b) => b.score - a.score || a.label.localeCompare(b.label));
}

/**
 * The typed parts inside each entity, addressed by ref: fields, property slots,
 * filled slots and projection fields. Selecting one of these is what the inspector's
 * type picker and the binding composer both act on.
 */
function partEntities(document: ProjectDocument) {
  const out: { ref: string; label: string; kind: string; detail: string }[] = [];

  for (const section of ["tables", "structs"] as const) {
    for (const item of sectionItems(document, section)) {
      for (const field of item.fields ?? []) {
        out.push({
          ref: buildRef(section === "tables" ? "table" : "struct", item.id, "field", field.name),
          label: field.name,
          kind: section === "tables" ? "table field" : "struct field",
          detail: typeLabel(field.logical_type),
        });
      }
    }
  }
  for (const component of sectionItems(document, "components")) {
    for (const property of component.properties ?? []) {
      out.push({
        ref: buildRef("component", component.id, "property", property.name),
        label: property.name,
        kind: "property slot",
        detail: typeLabel(property.logical_type),
      });
    }
  }
  for (const binding of sectionItems(document, "bindings")) {
    for (const property of binding.properties ?? []) {
      out.push({
        ref: buildRef("binding", binding.id, "property", property.name),
        label: property.name,
        kind: "filled slot",
        detail: binding.id,
      });
    }
  }
  for (const projection of sectionItems(document, "projections")) {
    for (const field of projection.fields ?? []) {
      out.push({
        ref: buildRef("projection", projection.id, "field", field.name),
        label: field.name,
        kind: "projection field",
        detail: projection.name,
      });
    }
  }
  // A ref whose id no longer resolves is not offered: dangling parts must not be
  // selectable from the palette.
  return out.filter((row) => {
    const parsed = parseRef(row.ref);
    const section = refSection(row.ref);
    return Boolean(parsed && section && findInSection(document, section, parsed.id));
  });
}
