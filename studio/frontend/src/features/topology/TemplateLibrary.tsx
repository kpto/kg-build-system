"use client";

/**
 * The mix-in template library.
 *
 * A template is not a vertex of the topology graph — it never reaches the blueprint, so
 * the metagraph the framework itself emits does not contain it. Drawing one on the canvas
 * made it float in the middle of the graph connected to nothing. It is a reusable bundle
 * of slots and annotations, so it gets a list here instead, and picking a row drives the
 * same inspector that edits any other component.
 *
 * The reason it is a list rather than nothing at all: a template mixed into no component
 * used to be indistinguishable from one that was merely off-screen. Here it says `unused`.
 */

import { useState } from "react";
import clsx from "clsx";

import { ChevronIcon, ProblemBadge, RowButton } from "@/components/ui";
import { useProblemsForRef } from "@/stores/problemStore";
import type { TemplateEntry } from "./logic";

export interface TemplateLibraryProps {
  entries: readonly TemplateEntry[];
  /** The globally selected IR ref, so the row for the open component reads as current. */
  selectedRef: string | null;
  onSelectRef(ref: string): void;
}

export function TemplateLibrary({ entries, selectedRef, onSelectRef }: TemplateLibraryProps) {
  const [open, setOpen] = useState(true);

  return (
    <div className="flex min-h-0 flex-col gap-1 border-t border-edge pt-1.5">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
        className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-muted hover:text-ink"
      >
        <ChevronIcon size={11} open={open} className="shrink-0 text-faint" />
        <span className="flex-1 text-left">mix-in templates</span>
        <span className="font-mono text-[9px] text-faint">{entries.length}</span>
      </button>

      {open && (
        <ul className="min-h-0 flex-1 overflow-auto">
          {entries.map((entry) => (
            <TemplateRow
              key={entry.component.id}
              entry={entry}
              active={selectedRef === `component:${entry.component.id}`}
              onSelectRef={onSelectRef}
            />
          ))}
          {entries.length === 0 && (
            <li className="px-1.5 py-1 text-[11px] text-faint">
              no templates — a template contributes slots and annotations to the components
              that mix it in
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

function TemplateRow({
  entry,
  active,
  onSelectRef,
}: {
  entry: TemplateEntry;
  active: boolean;
  onSelectRef(ref: string): void;
}) {
  const ref = `component:${entry.component.id}`;
  const problems = useProblemsForRef(ref);
  const { component, users, slotNames } = entry;
  const unused = users.length === 0;

  return (
    <li>
      <RowButton
        active={active}
        onActivate={() => onSelectRef(ref)}
        title={
          unused
            ? `${component.name} · ${component.kind} template · mixed into nothing`
            : `${component.name} · ${component.kind} template · mixed into ${users
                .map((user) => user.name)
                .join(", ")}`
        }
        className={clsx(
          "flex w-full items-center gap-1.5 rounded px-1.5 py-1 text-left hover:bg-raised",
          active && "bg-raised",
        )}
      >
        <span
          aria-hidden
          className="h-2.5 w-2.5 shrink-0 rotate-45 rounded-[2px] bg-template"
        />
        <span className="min-w-0 flex-1 truncate text-[12px] text-ink">{component.name}</span>
        {unused ? (
          <span className="shrink-0 font-mono text-[9px] uppercase text-warn">unused</span>
        ) : (
          <span className="shrink-0 font-mono text-[9px] text-faint">
            {users.length}
            {slotNames.length > 0 ? ` · ${slotNames.length} slots` : ""}
          </span>
        )}
        <ProblemBadge problems={problems} ref={ref} compact onClick={() => onSelectRef(ref)} />
      </RowButton>
    </li>
  );
}
