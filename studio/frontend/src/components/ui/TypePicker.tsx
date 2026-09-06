"use client";

import { useMemo } from "react";
import clsx from "clsx";

import type {
  LogicalType,
  NonNullableLogicalType,
  StructType,
  UnitName,
  UnitType,
} from "@/lib/ir";
import { array, isNullable, nullable, typeLabel, unit, unwrapNullable } from "@/lib/ir";
import { Select, type SelectOption } from "./Select";
import { Chip } from "./Chip";
import { Tooltip } from "./Tooltip";

/** A struct the picker may reference, addressed the way `StructType` is. */
export interface StructOption {
  readonly module: string;
  readonly qualname: string;
  /** The struct's own name, shown in the list instead of the generated class name. */
  readonly label?: string;
}

/**
 * The flat shape a type can be authored as: one optional outer nullable layer, one
 * optional array layer with its own item nullability, over one base (unit or struct).
 *
 * That is the studio's authoring vocabulary. Anything deeper (`Array[Array[int]]`) is
 * representable in the document but is not editable here, so it degrades to a
 * read-only chip plus a wholesale replacement rather than silently flattening the
 * user's type.
 */
export interface TypeDraft {
  readonly nullable: boolean;
  readonly array: boolean;
  readonly itemNullable: boolean;
  readonly base: UnitType | StructType;
}

export type TypeDraftOrOpaque =
  | ({ readonly kind: "draft" } & TypeDraft)
  | { readonly kind: "opaque"; readonly type: LogicalType };

/** Decompose a logical type into the editable shape, or mark it opaque. */
export function toTypeDraft(
  value: LogicalType | null | undefined,
): TypeDraftOrOpaque | null {
  if (value == null) return null;
  const outer = isNullable(value);
  const core: NonNullableLogicalType = outer ? unwrapNullable(value) : value;

  if (core.kind === "unit" || core.kind === "struct") {
    return { kind: "draft", nullable: outer, array: false, itemNullable: false, base: core };
  }
  if (core.kind === "array") {
    const item = core.item;
    if (item.kind === "array") return { kind: "opaque", type: value };
    const itemNullable = isNullable(item);
    const base = itemNullable ? unwrapNullable(item) : item;
    // `Array[Array[…]]` hides inside `unwrapNullable`'s return type, so re-check.
    if (base.kind === "array") return { kind: "opaque", type: value };
    return { kind: "draft", nullable: outer, array: true, itemNullable, base };
  }
  return { kind: "opaque", type: value };
}

/** The inverse of `toTypeDraft`, nesting in the order the label reads: `Array[int | None] | None`. */
export function fromTypeDraft(draft: TypeDraft): LogicalType {
  const base: NonNullableLogicalType =
    draft.base.kind === "struct"
      ? { kind: "struct", module: draft.base.module, qualname: draft.base.qualname }
      : unit(draft.base.name);
  const core: NonNullableLogicalType = draft.array
    ? array(draft.itemNullable ? nullable(base) : base)
    : base;
  return draft.nullable ? nullable(core) : core;
}

const FALLBACK_UNITS: readonly UnitName[] = [
  "bool",
  "int",
  "float",
  "str",
  "date",
  "time",
  "timestamp",
  "uuid",
];

export interface TypePickerProps {
  value: LogicalType | null | undefined;
  onChange(next: LogicalType): void;
  /** Canonical units from `/api/catalog → units`; falls back to the fixed vocabulary. */
  units?: readonly string[];
  structs?: readonly StructOption[];
  id?: string;
  disabled?: boolean;
  /** One-row layout for table cells. */
  compact?: boolean;
  className?: string;
}

/**
 * The visual logical-type editor, used by every type surface in the studio.
 *
 * Structure is composed by picking, never typed: choose a base (a canonical unit or a
 * struct declared in this document), wrap it in `Array[…]`, decide whether the items
 * are nullable, and whether the whole thing is. The chip below always shows the exact
 * `typeLabel` the generator will emit.
 */
export function TypePicker({
  value,
  onChange,
  units,
  structs = [],
  id,
  disabled = false,
  compact = false,
  className,
}: TypePickerProps) {
  const unitNames = useMemo(
    () => (units && units.length > 0 ? units : FALLBACK_UNITS).map((name) => String(name)),
    [units],
  );
  const draft = toTypeDraft(value);
  const label = typeLabel(value);

  const options = useMemo<SelectOption[]>(() => {
    const unitOptions: SelectOption[] = unitNames.map((name) => ({
      value: `unit:${name}`,
      label: name,
      group: "Canonical unit",
    }));
    const structOptions: SelectOption[] = structs.map((struct) => ({
      value: `struct:${struct.module}:${struct.qualname}`,
      label: struct.label ?? struct.qualname,
      group: "Project struct",
    }));
    return [...unitOptions, ...structOptions];
  }, [unitNames, structs]);

  if (draft === null) {
    return (
      <span className={clsx("studio-chip text-faint", className)} aria-label="No type set">
        no type
      </span>
    );
  }

  const pickBase = (raw: string): void => {
    if (!raw) return;
    const [kind, ...rest] = raw.split(":");
    const base: NonNullableLogicalType =
      kind === "struct"
        ? { kind: "struct", module: rest.slice(0, -1).join(":"), qualname: rest.at(-1) ?? "" }
        : unit((rest.join(":") || "str") as UnitName);
    onChange(
      draft.kind === "draft"
        ? fromTypeDraft({ ...draft, base })
        : isNullable(draft.type)
          ? nullable(base)
          : base,
    );
  };

  if (draft.kind === "opaque") {
    return (
      <div className={clsx("flex min-w-0 items-center gap-1.5", className)}>
        <Tooltip content="Nested array types are not editable here; picking a base replaces the whole type.">
          <Chip tone="warn">{label}</Chip>
        </Tooltip>
        <Select
          id={id}
          aria-label="Replace type"
          disabled={disabled}
          className="max-w-[10rem]"
          placeholder="replace…"
          options={options}
          onChange={(event) => pickBase(event.target.value)}
        />
      </div>
    );
  }

  const currentBase =
    draft.base.kind === "struct"
      ? `struct:${draft.base.module}:${draft.base.qualname}`
      : `unit:${draft.base.name}`;

  const patch = (changes: Partial<TypeDraft>) => onChange(fromTypeDraft({ ...draft, ...changes }));

  return (
    <div
      role="group"
      aria-label="Logical type"
      className={clsx(
        "min-w-0 gap-1.5",
        compact ? "flex flex-wrap items-center" : "flex flex-col",
        className,
      )}
    >
      <div className="flex min-w-0 flex-wrap items-center gap-1.5">
        <Select
          id={id}
          aria-label="Base type"
          disabled={disabled}
          className={compact ? "h-6 w-32 text-[11px]" : "w-40"}
          value={currentBase}
          options={options}
          onChange={(event) => pickBase(event.target.value)}
        />
        <LayerToggle
          label="Array[…]"
          active={draft.array}
          disabled={disabled}
          onClick={() =>
            patch(draft.array ? { array: false, itemNullable: false } : { array: true })
          }
        />
        <LayerToggle
          label="items | None"
          active={draft.array && draft.itemNullable}
          disabled={disabled || !draft.array}
          onClick={() => patch({ itemNullable: !draft.itemNullable })}
        />
        <LayerToggle
          label="| None"
          active={draft.nullable}
          disabled={disabled}
          onClick={() => patch({ nullable: !draft.nullable })}
        />
      </div>
      <div className="flex min-w-0 items-center gap-1.5">
        <span className="text-[10px] uppercase tracking-[0.06em] text-faint">type</span>
        <Chip
          tone={draft.nullable ? "warn" : draft.base.kind === "struct" ? "node" : "neutral"}
          title={label}
          className="max-w-full"
        >
          {label || "—"}
        </Chip>
      </div>
    </div>
  );
}

function LayerToggle({
  label,
  active,
  disabled,
  onClick,
}: {
  label: string;
  active: boolean;
  disabled: boolean;
  onClick(): void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      title={active ? `Remove ${label}` : `Wrap in ${label}`}
      className={clsx(
        "h-6 rounded-md border px-1.5 font-mono text-[11px] transition-colors",
        active
          ? "border-info/70 bg-info/15 text-ink"
          : "border-edge bg-raised text-muted hover:border-edge-strong hover:text-ink",
        disabled && "cursor-not-allowed opacity-40",
      )}
    >
      {label}
    </button>
  );
}
