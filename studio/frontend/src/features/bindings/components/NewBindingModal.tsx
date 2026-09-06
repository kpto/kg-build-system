"use client";

/**
 * Creating a binding.
 *
 * Two rules the form enforces rather than explains: the target must be a **concrete**
 * component (an abstract category is refused by `binding/factories.py` with
 * "target must be a concrete node component"), and the `build_key` must be a non-null
 * scalar — so the seed picker offers scalar fields and wraps a nullable one in
 * `where_present` before the key is ever written.
 */

import { useEffect, useMemo, useState } from "react";

import { Chip, Modal, Select, type SelectOption } from "@/components/ui";
import { typeLabel } from "@/lib/ir";
import type { ProjectDocument } from "@/lib/ir";
import type { BindingContext } from "../logic/context";
import { bindableComponents } from "../logic/rules";
import { selectables, selectableByName, selectablePaths } from "../logic/context";
import { createBinding, type NewBindingSeed } from "../logic/edits";
import { isNullable, unwrapNullable } from "@/lib/ir";

export interface NewBindingModalProps {
  ctx: BindingContext;
  open: boolean;
  onClose(): void;
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
  onCreated(bindingId: string): void;
  /** What another area already knows: bind this projection/table (and, if known, the output it came from). */
  seed?: { readonly source?: string; readonly field?: string };
}

export function NewBindingModal({ ctx, open, onClose, apply, onCreated, seed }: NewBindingModalProps) {
  const components = useMemo(() => bindableComponents(ctx), [ctx]);
  const [componentId, setComponentId] = useState("");
  const [source, setSource] = useState("");
  const [path, setPath] = useState("");

  // Each opening starts from the caller's knowledge, not from wherever the last one
  // was left; a stale source here silently changes which key gets composed.
  useEffect(() => {
    if (!open) return;
    // Resolved through `selectableByName` so a seed carrying either the source's name
    // or its id lands on the same entry; a group member's two spellings differ.
    const entry = selectableByName(ctx, seed?.source);
    // A seeded field is only usable as the key if it is a scalar; otherwise leave the
    // key to be picked, since a build key must not be a row or a list.
    const seededPath =
      entry && seed?.field
        ? (selectablePaths(ctx, entry) ?? []).find(
            (item) => item.path.join(".") === seed.field && unwrapNullable(item.logical_type).kind === "unit",
          )
        : undefined;
    setComponentId("");
    setSource(entry?.name ?? "");
    setPath(seededPath ? seededPath.path.join(".") : "");
  }, [open, seed, ctx]);

  const entry = selectables(ctx).find((item) => item.name === source) ?? null;
  const paths = entry ? selectablePaths(ctx, entry) : [];
  const scalarPaths = paths.filter((item) => {
    const base = unwrapNullable(item.logical_type);
    return base.kind === "unit";
  });
  const chosen = scalarPaths.find((item) => item.path.join(".") === path) ?? null;
  const unwrap = chosen ? isNullable(chosen.logical_type) : false;

  const componentOptions: SelectOption[] = components.map((component) => ({
    value: component.id,
    label: `${component.declaration_name}  ·  ${component.kind}`,
    group: component.kind === "node" ? "node components" : "edge components",
  }));

  const create = () => {
    if (!componentId || !chosen) return;
    const seed: NewBindingSeed = { component: componentId, source, path: chosen.path, unwrap };
    const id = `${componentId}_binding`;
    apply(createBinding(ctx, seed));
    onCreated(id);
    onClose();
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New binding"
      size="sm"
      footer={
        <>
          <button
            type="button"
            onClick={create}
            disabled={!componentId || !chosen}
            className="rounded-md border border-info/60 bg-info/15 px-2 py-1 text-[12px] text-ink hover:bg-info/25 disabled:opacity-40"
          >
            create
          </button>
          <button type="button" onClick={onClose} className="rounded-md border border-edge px-2 py-1 text-[12px] text-muted hover:text-ink">
            cancel
          </button>
        </>
      }
    >
      <div className="flex flex-col gap-2">
        <Row label="component" hint="only concrete components can be bound">
          <Select
            aria-label="target component"
            value={componentId}
            options={componentOptions}
            placeholder="pick a concrete component"
            onChange={(event) => setComponentId(event.target.value)}
          />
        </Row>
        <Row label="source" hint="the table or projection the key reads">
          <Select
            aria-label="key source"
            value={source}
            options={selectables(ctx).map((item) => ({
              value: item.name,
              label: item.group ? `${item.group}.${item.name}` : item.name,
              group: item.kind === "table" ? "tables" : "projections",
            }))}
            placeholder="pick a table or projection"
            onChange={(event) => {
              setSource(event.target.value);
              setPath("");
            }}
          />
        </Row>
        <Row label="key field" hint="a scalar; a nullable one is seeded already unwrapped">
          <Select
            aria-label="key field"
            value={path}
            options={scalarPaths.map((item) => ({
              value: item.path.join("."),
              label: `${item.path.join(".")}  ·  ${typeLabel(item.logical_type)}`,
            }))}
            placeholder={scalarPaths.length === 0 ? "this source declares no scalar field" : "pick the key column"}
            onChange={(event) => setPath(event.target.value)}
          />
        </Row>
        {chosen && (
          <p className="text-[11px] leading-snug text-muted">
            build_key seeds as{" "}
            <code className="font-mono text-[11px] text-relation">
              {`${source}.${chosen.path.join(".")}${unwrap ? ".where_present()" : ""}`}
            </code>
            {unwrap && (
              <Chip tone="warn" className="ml-1.5">
                nullable → keep rows where present
              </Chip>
            )}
          </p>
        )}
      </div>
    </Modal>
  );
}

function Row({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[6rem_1fr] items-center gap-2">
      <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-muted">{label}</span>
      <div className="min-w-0">{children}</div>
      <span className="col-span-2 pl-[6rem] text-[10px] text-faint">{hint}</span>
    </div>
  );
}
