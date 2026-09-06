"use client";

/**
 * The source block: which table or projection, and which flattened path inside it.
 *
 * Nested struct members are chosen from `index.selectable[].paths`, which the backend
 * already flattened, so a deep member is one pick rather than a drill the UI has to
 * re-derive — and because the base is still a plain field reference, the whole chain
 * stays folded (`pick` folds a path).
 */

import { Select, type SelectOption } from "@/components/ui";
import { typeLabel } from "@/lib/ir";
import type { Block } from "../logic/stack";
import type { BindingContext } from "../logic/context";
import { selectableByName, selectablePaths, selectables } from "../logic/context";

export interface SourceControlProps {
  ctx: BindingContext;
  block: Block;
  onSelectSource(name: string): void;
  onSelectPath(path: readonly string[]): void;
}

export function SourceControl(props: SourceControlProps) {
  const { ctx, block } = props;
  if (block.kind === "literal") {
    return (
      <p className="font-mono text-[11px] text-relation">
        {JSON.stringify(block.value)} <span className="text-faint">· {typeLabel(block.type)}</span>
      </p>
    );
  }
  if (block.kind !== "source") return null;

  const entry = selectableByName(ctx, block.source);
  const paths = entry ? selectablePaths(ctx, entry) : [];
  const current = block.path.join(".");
  const depth = current.split(".").length;

  const sourceOptions: SelectOption[] = selectables(ctx).map((item) => ({
    value: item.name,
    label: item.group ? `${item.group}.${item.name}` : item.name,
    group: item.kind === "table" ? "tables" : "projections",
  }));

  // Two groups, so the author can drill in *and* step back out: the source's own
  // columns, and one more struct member below wherever the path currently is. The
  // candidates are the flattened paths the backend computed, never a walk of our own.
  const columns: SelectOption[] = paths
    .filter((path) => path.path.length === 1)
    .map((path) => ({
      value: path.path.join("."),
      label: `${path.path[0]}  ·  ${typeLabel(path.logical_type)}`,
      group: `${entry?.name ?? "source"} columns`,
    }));
  const deeper: SelectOption[] =
    block.path.length === 0
      ? []
      : paths
          .filter((path) => path.path.length === depth + 1 && path.path.join(".").startsWith(`${current}.`))
          .map((path) => ({
            value: path.path.join("."),
            label: `${path.path[depth]}  ·  ${typeLabel(path.logical_type)}`,
            group: `inside ${current}`,
          }));
  const pathOptions = [...deeper, ...columns];

  return (
    <div className="flex flex-col gap-1.5">
      <div className="grid grid-cols-[5.5rem_1fr] items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-muted">from</span>
        <Select
          aria-label="source"
          value={block.source}
          options={sourceOptions}
          placeholder="pick a table or projection"
          onChange={(event) => props.onSelectSource(event.target.value)}
        />
      </div>
      <div className="grid grid-cols-[5.5rem_1fr] items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-muted">field</span>
        <Select
          aria-label="field path"
          value={paths.some((path) => path.path.join(".") === current) ? current : ""}
          options={pathOptions}
          placeholder={paths.length === 0 ? "this source declares no fields" : "pick a field"}
          invalid={block.path.length === 0}
          onChange={(event) => props.onSelectPath(event.target.value ? event.target.value.split(".") : [])}
        />
      </div>
      {entry && (
        <p className="font-mono text-[10px] text-faint">
          {entry.declaration_name}.{block.path.join(".") || "?"}
          {entry.group ? `  ·  group ${entry.group}` : ""}
        </p>
      )}
    </div>
  );
}
