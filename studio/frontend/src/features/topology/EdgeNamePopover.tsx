"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { Button, Chip, Field, TextInput, Toggle } from "@/components/ui";
import type { ProjectDocument } from "@/lib/ir";
import { componentById, deriveIdentity } from "./logic";

export interface EdgeDraft {
  sourceId: string;
  targetId: string;
  /** Screen position the popover opens at, in the flow container's client box. */
  x: number;
  y: number;
}

export interface EdgeNamePopoverProps {
  document: ProjectDocument;
  draft: EdgeDraft;
  /** Whether an edge category already covers this endpoint pair. */
  categoryExists: boolean;
  onClose(): void;
  onConfirm(input: { predicate: string; label: string; createCategory: boolean }): void;
}

const upperSlug = (value: string): string =>
  value.trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "RELATES";

/**
 * The inline "name this relationship" popover.
 *
 * A port-to-port drag is the composition act; this only captures the two text values
 * (predicate and label) and the single choice the endpoint pair forces — whether to also
 * create the category edge the concrete edge legally needs when none exists yet. The
 * endpoints themselves were chosen by the drag, so they are shown, never re-typed.
 */
export function EdgeNamePopover({
  document,
  draft,
  categoryExists,
  onClose,
  onConfirm,
}: EdgeNamePopoverProps) {
  const source = componentById(document, draft.sourceId);
  const target = componentById(document, draft.targetId);
  const [predicate, setPredicate] = useState("");
  const [label, setLabel] = useState("");
  const [touchedLabel, setTouchedLabel] = useState(false);
  const [createCategory, setCreateCategory] = useState(!categoryExists);
  const box = useRef<HTMLDivElement | null>(null);

  // Keep the popover inside the viewport-ish by clamping near its opening point.
  const style = useMemo(() => {
    const width = 300;
    const left = Math.max(8, Math.min(draft.x, (typeof window !== "undefined" ? window.innerWidth : 1200) - width - 8));
    return { left, top: Math.max(8, draft.y) };
  }, [draft.x, draft.y]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.stopPropagation();
        onClose();
      }
      if (event.key === "Enter" && predicate.trim()) {
        event.preventDefault();
        confirm();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [predicate, label, createCategory]);

  const derived = predicate.trim() ? deriveIdentity(document, predicate, "edge", "concrete") : null;

  const confirm = () => {
    if (!predicate.trim()) return;
    onConfirm({
      predicate: predicate.trim(),
      label: (touchedLabel ? label : upperSlug(predicate)).trim() || upperSlug(predicate),
      createCategory,
    });
  };

  return (
    <div
      ref={box}
      role="dialog"
      aria-label="Name this relationship"
      data-testid="edge-name-popover"
      className="studio-card absolute z-40 w-[19rem] p-2.5 shadow-xl"
      style={style}
    >
      <div className="mb-2 flex items-center gap-1.5 text-[11px]">
        <Chip tone="node" className="max-w-[7rem]">{source?.name ?? draft.sourceId}</Chip>
        <span className="text-relation" aria-hidden>→</span>
        <Chip tone="node" className="max-w-[7rem]">{target?.name ?? draft.targetId}</Chip>
      </div>

      <div className="flex flex-col gap-2">
        <Field label="predicate" htmlFor="edge-predicate" required stack>
          <TextInput
            id="edge-predicate"
            autoFocus
            value={predicate}
            placeholder="e.g. has unit"
            onChange={(event) => setPredicate(event.target.value)}
          />
        </Field>
        {derived && (
          <p className="font-mono text-[10px] text-faint">
            id <span className="text-ink">{derived.id}</span>
          </p>
        )}
        <Field label="label" htmlFor="edge-label" stack hint="the semantic edge label the graph carries">
          <TextInput
            id="edge-label"
            value={touchedLabel ? label : upperSlug(predicate)}
            placeholder="HAS_UNIT"
            onFocus={() => !touchedLabel && setLabel(upperSlug(predicate))}
            onChange={(event) => {
              setTouchedLabel(true);
              setLabel(event.target.value);
            }}
          />
        </Field>

        <div className="rounded border border-edge bg-raised px-2 py-1.5">
          {categoryExists ? (
            <p className="text-[11px] text-muted">
              A category edge already spans this pair — the new edge descends from it.
            </p>
          ) : (
            <Toggle
              label="also create a category edge"
              description="a concrete edge needs a category parent over these endpoint categories"
              checked={createCategory}
              onChange={setCreateCategory}
            />
          )}
        </div>
      </div>

      <div className="mt-2.5 flex justify-end gap-2">
        <Button size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button size="sm" variant="primary" disabled={!predicate.trim() || (!categoryExists && !createCategory)} onClick={confirm}>
          Create edge
        </Button>
      </div>
    </div>
  );
}
