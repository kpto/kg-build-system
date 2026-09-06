"use client";

/**
 * The controls one block exposes.
 *
 * Every value a block needs is picked or typed here — a separator, a fallback, the
 * member of a struct, a predicate — because free text is only allowed where text *is*
 * the value (DESIGN.md §5). The control is chosen by the operand's logical type, and a
 * struct or a list of structs is refused outright: `expressions/literals.py` will not
 * build a literal that embeds a record.
 */

import { Select, TextInput, type SelectOption } from "@/components/ui";
import type { Expression, JsonValue, LogicalType } from "@/lib/ir";
import { isNullable, typeLabel, unwrapNullable } from "@/lib/ir";
import type { Operand } from "../logic/stack";
import type { BindingContext } from "../logic/context";
import { selectableByName, selectablePaths } from "../logic/context";

export interface OperandControlProps {
  ctx: BindingContext;
  /** The operand's required type, derived from the block's position in the stack. */
  required: LogicalType | null;
  operand: Operand | undefined;
  label: string;
  hint?: string;
  /** Only paths of this source are offered for a field operand (one source per stack). */
  source: string | null;
  onChange(operand: Operand): void;
}

const TEXT_CANONICAL = new Set(["date", "time", "timestamp", "uuid"]);

export function OperandControl({ ctx, required, operand, label, hint, source, onChange }: OperandControlProps) {
  const id = `operand-${label.replace(/\W+/g, "-")}`;
  const base = required ? unwrapNullable(required) : null;

  if (base && (base.kind === "struct" || (base.kind === "array" && unwrapNullable(base.item).kind === "struct"))) {
    // A struct value cannot be a literal at all, so the only honest operand is a
    // reference to one the source declares.
    return (
      <FieldRow label={label} hint={hint ?? "a record cannot be written down — read one from the table"}>
        <FieldPicker ctx={ctx} source={source} required={required} value={operand} onChange={onChange} />
      </FieldRow>
    );
  }

  if (operand?.kind === "passthrough") {
    return (
      <FieldRow label={label} hint="written by hand or by script; delete this block to rewrite it">
        <code className="truncate rounded border border-edge bg-raised px-1.5 py-1 font-mono text-[11px] text-relation">
          {expressionPreview(operand.expression)}
        </code>
      </FieldRow>
    );
  }

  if (operand?.kind === "field") {
    return (
      <FieldRow label={label} hint={hint ?? `read from ${operand.source}.${operand.path.join(".")}`}>
        <FieldPicker ctx={ctx} source={source} required={required} value={operand} onChange={onChange} />
      </FieldRow>
    );
  }

  const value = operand?.kind === "literal" ? operand.value : undefined;

  if (base?.kind === "array") {
    const items = Array.isArray(value) ? (value as JsonValue[]) : [];
    return (
      <FieldRow label={label} hint={hint ?? `a list of ${typeLabel(base.item)}, comma separated`}>
        <TextInput
          id={id}
          mono
          value={items.map((item) => (typeof item === "string" ? item : JSON.stringify(item))).join(", ")}
          onChange={(event) => {
            const text = event.target.value;
            const parts = text.length === 0 ? [] : text.split(",");
            onChange({
              slot: operand?.slot ?? 1,
              kind: "literal",
              value: parts.map((part) => coerce(part.trim(), base.item)),
              type: required as LogicalType,
            });
          }}
        />
      </FieldRow>
    );
  }

  if (base?.kind === "unit" && base.name === "bool") {
    return (
      <FieldRow label={label} hint={hint}>
        <Select
          id={id}
          value={value === undefined ? "" : String(Boolean(value))}
          options={[
            { value: "true", label: "true" },
            { value: "false", label: "false" },
          ]}
          placeholder="set a value"
          onChange={(event) =>
            onChange({
              slot: operand?.slot ?? 1,
              kind: "literal",
              value: event.target.value === "true",
              type: required as LogicalType,
            })
          }
        />
      </FieldRow>
    );
  }

  if (base?.kind === "unit" && (base.name === "int" || base.name === "float")) {
    return (
      <FieldRow label={label} hint={hint ?? base.name}>
        <TextInput
          id={id}
          mono
          inputMode="decimal"
          value={value === undefined || value === null ? "" : String(value)}
          onChange={(event) =>
            onChange({
              slot: operand?.slot ?? 1,
              kind: "literal",
              value: Number(event.target.value),
              type: required as LogicalType,
            })
          }
        />
      </FieldRow>
    );
  }

  const canonical = base?.kind === "unit" && TEXT_CANONICAL.has(base.name);
  return (
    <FieldRow
      label={label}
      hint={hint ?? (canonical ? `canonical ${base?.kind === "unit" ? base.name : ""} text, e.g. ${exampleFor(String(base?.kind === "unit" ? base.name : ""))}` : undefined)}
    >
      <div className="flex items-center gap-1.5">
        <TextInput
          id={id}
          mono
          placeholder={canonical ? exampleFor(String(base?.kind === "unit" ? base.name : "")) : "text"}
          value={typeof value === "string" ? value : value === undefined || value === null ? "" : String(value)}
          onChange={(event) =>
            onChange({
              slot: operand?.slot ?? 1,
              kind: "literal",
              value: event.target.value,
              type: required as LogicalType,
            })
          }
        />
        <button
          type="button"
          title="read this value from the table instead"
          className="shrink-0 rounded border border-edge bg-raised px-1.5 py-1 font-mono text-[10px] text-muted hover:border-edge-strong hover:text-ink"
          onClick={() =>
            onChange({ slot: operand?.slot ?? 1, kind: "field", source: source ?? "", path: [] })
          }
        >
          field
        </button>
      </div>
    </FieldRow>
  );
}

function FieldPicker({
  ctx,
  source,
  required,
  value,
  onChange,
}: {
  ctx: BindingContext;
  source: string | null;
  required: LogicalType | null;
  value: Operand | undefined;
  onChange(operand: Operand): void;
}) {
  const entry = selectableByName(ctx, source);
  const paths = entry ? selectablePaths(ctx, entry) : [];
  const options: SelectOption[] = paths
    .filter((path) => (required == null ? true : sameShape(path.logical_type, required)))
    .map((path) => ({
      value: path.path.join("."),
      label: `${path.path.join(".")}  ·  ${typeLabel(path.logical_type)}`,
    }));
  const current = value?.kind === "field" ? value.path.join(".") : "";
  return (
    <Select
      value={options.some((option) => option.value === current) ? current : ""}
      options={options}
      placeholder={options.length === 0 ? "nothing of that type in this source" : "pick a field"}
      onChange={(event) =>
        onChange({
          slot: value?.slot ?? 1,
          kind: "field",
          source: source ?? "",
          path: event.target.value ? event.target.value.split(".") : [],
        })
      }
    />
  );
}

function sameShape(candidate: LogicalType, required: LogicalType): boolean {
  const left = unwrapNullable(candidate);
  const right = unwrapNullable(required);
  const sameBase =
    left.kind === right.kind &&
    (left.kind !== "unit" || (right.kind === "unit" && left.name === right.name)) &&
    (left.kind !== "struct" || (right.kind === "struct" && left.qualname === right.qualname)) &&
    (left.kind !== "array" ||
      (right.kind === "array" && typeLabel(left.item).replace(" | None", "") === typeLabel(right.item).replace(" | None", "")));
  // A nullable slot also accepts a non-null field, so both are offered.
  return sameBase && (!isNullable(required) || isNullable(candidate) || true);
}

function coerce(text: string, type: LogicalType): JsonValue {
  const base = unwrapNullable(type);
  if (base.kind === "unit") {
    if (base.name === "int" || base.name === "float") return Number(text);
    if (base.name === "bool") return text === "true";
  }
  return text;
}

function exampleFor(unit: string): string {
  if (unit === "date") return "2026-08-01";
  if (unit === "time") return "12:30:00";
  if (unit === "timestamp") return "2026-08-01T12:30:00";
  if (unit === "uuid") return "3f6f0a1e-2b3c-4d5e-8f90-112233445566";
  return "";
}

function expressionPreview(expression: Expression): string {
  if (expression.kind === "field") return `${expression.source}.${(expression.path ?? []).join(".")}`;
  if (expression.kind === "literal") return JSON.stringify(expression.value ?? null);
  return `${expression.operator}(…)`;
}

function FieldRow({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[5.5rem_1fr] items-center gap-2">
      <span className="truncate text-[11px] font-medium uppercase tracking-[0.05em] text-muted">{label}</span>
      <div className="min-w-0">{children}</div>
      {hint && <span className="col-span-2 truncate pl-[5.5rem] text-[10px] text-faint">{hint}</span>}
    </div>
  );
}
