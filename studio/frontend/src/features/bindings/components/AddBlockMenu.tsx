"use client";

/**
 * The add-block menu: the catalogue, filtered against the tip.
 *
 * Enabled entries are operators the framework would compile in this position; every
 * disabled entry still shows, with the rule that stopped it and the block to add
 * first. Keeping the refusals visible is deliberate — the author learns the type model
 * from the menu rather than hitting a wall.
 */

import { useEffect, useRef, useState } from "react";

import { Chip, Tooltip } from "@/components/ui";
import type { LogicalType } from "@/lib/ir";
import { typeLabel } from "@/lib/ir";
import { GROUP_ORDER } from "../logic/stack";
import type { PaletteEntry } from "../logic/palette";

export interface AddBlockMenuProps {
  entries: PaletteEntry[];
  tip: LogicalType | null;
  /** An entry chosen; `entry` is the palette row, which carries `concat`'s side. */
  onPick(entry: PaletteEntry): void;
  /** Insert the block the refusal named (Keep rows where present, Drop missing items). */
  onFix(entry: PaletteEntry): void;
  onClose(): void;
}

export function AddBlockMenu({ entries, tip, onPick, onFix, onClose }: AddBlockMenuProps) {
  const [pending, setPending] = useState<PaletteEntry | null>(null);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    const onClick = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) onClose();
    };
    window.addEventListener("keydown", onKey);
    window.addEventListener("mousedown", onClick);
    return () => {
      window.removeEventListener("keydown", onKey);
      window.removeEventListener("mousedown", onClick);
    };
  }, [onClose]);

  const groups = GROUP_ORDER.map((group) => ({
    group,
    items: entries.filter((entry) => entry.group === group),
  })).filter((section) => section.items.length > 0);

  return (
    <div
      ref={ref}
      className="studio-card absolute bottom-2 left-2 right-2 z-30 flex max-h-[26rem] flex-col overflow-hidden bg-overlay/95 shadow-xl"
      role="dialog"
      aria-label="Add a block"
    >
      <header className="flex h-7 shrink-0 items-center gap-2 border-b border-edge px-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">Add a block</h3>
        <span className="font-mono text-[10px] text-info">on {tip == null ? "nothing yet" : typeLabel(tip)}</span>
        <button type="button" onClick={onClose} aria-label="Close" className="ml-auto rounded px-1 text-[12px] text-faint hover:text-ink">
          ×
        </button>
      </header>
      <div className="min-h-0 flex-1 overflow-auto p-1.5">
        {groups.map((section) => (
          <section key={section.group} className="mb-1.5">
            <h4 className="px-1 py-0.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-faint">
              {section.group}
            </h4>
            <ul className="flex flex-col gap-0.5">
              {section.items.map((entry) => (
                <PaletteRow
                  key={`${entry.operator}${entry.side ?? ""}`}
                  entry={entry}
                  pending={pending?.operator === entry.operator && pending?.side === entry.side}
                  onPick={onPick}
                  onPending={setPending}
                  onFix={onFix}
                />
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

function PaletteRow({
  entry,
  pending,
  onPick,
  onPending,
  onFix,
}: {
  entry: PaletteEntry;
  pending: boolean;
  onPick(entry: PaletteEntry): void;
  onPending(entry: PaletteEntry): void;
  onFix(entry: PaletteEntry): void;
}) {
  if (entry.enabled) {
    return (
      <li>
        <button
          type="button"
          onClick={() => onPick(entry)}
          className="flex w-full items-start gap-2 rounded px-1.5 py-1 text-left hover:bg-raised"
        >
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[12px] text-ink">{entry.label}</span>
            {entry.docs && <span className="block truncate text-[10px] text-faint">{entry.docs}</span>}
          </span>
          {entry.side && <SideMark side={entry.side} />}
        </button>
      </li>
    );
  }

  return (
    <li className="flex items-start gap-2 rounded px-1.5 py-1 opacity-70">
      <span className="min-w-0 flex-1">
        <span className="block truncate text-[12px] text-muted line-through decoration-edge-strong">
          {entry.label}
        </span>
        <span className="block text-[10px] leading-snug text-warn">{entry.reason}</span>
      </span>
      {entry.side && <SideMark side={entry.side} muted />}
      {entry.fix && pending && (
        <button
          type="button"
          onClick={() => onFix(entry)}
          className="shrink-0 rounded border border-info/60 bg-info/15 px-1.5 py-0.5 text-[10px] text-ink hover:bg-info/25"
        >
          + {entry.fix.label}
        </button>
      )}
      {entry.fix && !pending && (
        <Tooltip content="why is this unavailable?" side="left">
          <button
            type="button"
            onClick={() => onPending(entry)}
            className="shrink-0 rounded border border-edge px-1 py-0.5 text-[10px] text-muted hover:border-edge-strong hover:text-ink"
          >
            how?
          </button>
        </Tooltip>
      )}
      {!entry.fix && (
        <Chip tone="neutral" title={entry.reason ?? undefined} className="shrink-0">
          n/a
        </Chip>
      )}
    </li>
  );
}

/** The two sides of `concat` shown as the two orders they are. */
export function SideMark({ side, muted }: { side: "prepend" | "append"; muted?: boolean }) {
  const value = side === "prepend" ? "value + stack" : "stack + value";
  return (
    <span
      className={
        muted
          ? "shrink-0 rounded border border-edge px-1 font-mono text-[9px] text-faint"
          : "shrink-0 rounded border border-edge bg-raised px-1 font-mono text-[9px] text-muted"
      }
      title={`emits concat(${value})`}
    >
      {value}
    </span>
  );
}

/** The closed affordance, kept beside the menu so the caller renders one thing. */
export function AddBlockButton({ onClick, disabled, tip }: { onClick(): void; disabled: boolean; tip: LogicalType | null }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={disabled ? "pick a field to start the stack" : `add a block under ${typeLabel(tip)}`}
      className="flex h-7 items-center gap-1.5 rounded-md border border-dashed border-edge px-2 text-[11px] text-muted hover:border-info hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
    >
      <span aria-hidden>+</span> add a block
      {tip && <span className="font-mono text-[10px] text-faint">on {typeLabel(tip)}</span>}
    </button>
  );
}
