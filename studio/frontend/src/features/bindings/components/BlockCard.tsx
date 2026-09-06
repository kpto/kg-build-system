"use client";

/**
 * One block of the stack, and the seam under it.
 *
 * The block says what it does (its catalogue label and `docs` sentence), takes its
 * parameters inline, and hands its resulting logical type to the seam beneath it —
 * that seam is what the next block's palette is filtered against, so it has to be
 * visible (DESIGN.md §5).
 */

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Select, Tooltip } from "@/components/ui";
import type { LogicalType } from "@/lib/ir";
import { typeLabel } from "@/lib/ir";
import type { Block, OperationBlock, Operand } from "../logic/stack";
import { labelFor } from "../logic/stack";
import type { OperatorEntry } from "@/lib/types";
import { OperandControl } from "./OperandControl";
import { SourceControl } from "./SourceControl";
import { memberNameOf } from "../logic/preview";
import type { BindingContext } from "../logic/context";

export interface BlockCardProps {
  ctx: BindingContext;
  block: Block;
  index: number;
  count: number;
  /** The head block, so a parameter can offer fields of the same source. */
  head: Block | undefined;
  /** The value handed *into* this block, which types its parameters. */
  input: LogicalType | null;
  /** The value this block hands down: the seam. */
  output: LogicalType | null;
  operator?: OperatorEntry;
  /** Blocks that would go away if this one did. */
  downstream: number;
  pendingDelete: boolean;
  onSelectSource(name: string): void;
  onSelectPath(path: readonly string[]): void;
  onRenameMember(name: string): void;
  onOperand(slot: number, operand: Operand): void;
  onDelete(index: number): void;
}

export function BlockCard(props: BlockCardProps) {
  const { block, index, count, output, downstream } = props;
  const sortable = useSortable({ id: block.id, disabled: block.role === "head" });

  return (
    <li
      ref={sortable.setNodeRef}
      style={{
        transform: CSS.Transform.toString(sortable.transform),
        transition: sortable.isDragging ? undefined : sortable.transition,
        opacity: sortable.isDragging ? 0.55 : 1,
      }}
      className="flex flex-col"
    >
      <div className="studio-card flex flex-col gap-1.5 p-2">
        <header className="flex items-center gap-1.5">
          {block.role === "step" && (
            <button
              type="button"
              {...(sortable.attributes ?? {})}
              {...(sortable.listeners ?? {})}
              aria-label={`Reorder ${labelFor(block)}`}
              title="Drag to reorder; an invalid order is refused with the reason"
              className="shrink-0 cursor-grab rounded px-1 font-mono text-[12px] leading-none text-faint hover:text-ink"
            >
              ⠿
            </button>
          )}
          <span className="min-w-0 flex-1 truncate text-[12px] font-medium text-ink">{title(props)}</span>
          <span className="shrink-0 font-mono text-[10px] text-faint">
            {block.kind === "source" ? "source" : (props.operator?.group ?? "step")}
          </span>
          <button
            type="button"
            onClick={() => props.onDelete(index)}
            aria-expanded={props.pendingDelete}
            aria-label={
              downstream > 0
                ? `Remove ${labelFor(block)} — this also removes ${downstream} downstream block${downstream === 1 ? "" : "s"}`
                : `Remove ${labelFor(block)}`
            }
            title={
              downstream > 0
                ? `this also removes ${downstream} downstream block${downstream === 1 ? "" : "s"}`
                : "remove this block"
            }
            className={
              downstream > 0
                ? "shrink-0 rounded border border-warn/50 bg-warn/10 px-1 font-mono text-[10px] text-warn hover:bg-warn/20"
                : "shrink-0 rounded px-1 font-mono text-[12px] leading-none text-faint hover:text-danger"
            }
          >
            ×{downstream > 0 ? `+${downstream}` : ""}
          </button>
        </header>

        {block.kind === "operation" ? <BlockParameters {...props} /> : <SourceControl {...props} />}

        {block.kind === "operation" && props.operator?.docs && (
          <p className="text-[11px] leading-snug text-muted">{props.operator.docs}</p>
        )}

        {index < count - 1 && sideNote(block) && (
          <p className="text-[10px] leading-snug text-faint">{sideNote(block)}</p>
        )}
      </div>
      <Seam type={output} last={index === count - 1} />
    </li>
  );
}

function title({ block, operator }: BlockCardProps): string {
  if (block.kind === "source") return "Source";
  if (block.kind === "literal") return "Written value";
  if (block.operator === "concat") return block.side === "prepend" ? "Put text in front" : "Put text behind";
  return operator?.label ?? labelFor(block);
}

/** The row effect and, for `concat`, the argument order that says which side. */
function sideNote(block: Block): string {
  if (block.kind !== "operation") return "";
  if (block.operator === "concat") {
    return block.side === "prepend"
      ? "concat(value, this) — the text is written in front"
      : "concat(this, value) — the text is written behind";
  }
  if (block.operator === "where_present") return "row effect: the rows with no value are dropped";
  if (block.operator === "coalesce") return "row effect: every row is kept, the missing ones take the fallback";
  if (block.operator === "keep_if") return "row effect: the rows failing the test are dropped";
  if (block.operator === "expand") return "row effect: one row per item of the list";
  if (block.operator === "without_nulls") return "item effect: the missing items are dropped, no row is lost";
  return "";
}

/** The resulting logical type, written on the join between two blocks. */
export function Seam({ type, last }: { type: LogicalType | null; last: boolean }) {
  return (
    <div className="flex h-5 items-center gap-1.5 pl-3">
      <span className="h-full w-px bg-edge" aria-hidden />
      <span
        className="rounded border border-edge bg-raised px-1 font-mono text-[10px] text-info"
        title={type == null ? "the stack does not resolve yet" : `this value is ${typeLabel(type)}`}
      >
        {type == null ? "—" : typeLabel(type)}
      </span>
      {last && <span className="text-[10px] text-faint">→ the value this stack produces</span>}
    </div>
  );
}

function BlockParameters(props: BlockCardProps) {
  const { ctx, block, input } = props;
  if (block.kind !== "operation") return null;

  if (block.operator === "struct_field" || block.operator === "map_items") {
    const options = memberOptions(ctx, input);
    return (
      <div className="flex flex-col gap-1.5">
        <div className="grid grid-cols-[5.5rem_1fr] items-center gap-2">
          <span className="text-[11px] font-medium uppercase tracking-[0.05em] text-muted">member</span>
          <Select
            aria-label="member"
            value={typeof block.parameters["name"] === "string" ? String(block.parameters["name"]) : ""}
            options={options}
            placeholder={options.length === 0 ? "this record declares no members" : "pick a member"}
            onChange={(event) => props.onRenameMember(event.target.value)}
          />
        </div>
        {options.length === 0 && (
          <p className="text-[10px] text-danger">the record above declares no members to read</p>
        )}
      </div>
    );
  }

  const specs = operandSpecs(block);
  if (specs.length === 0) return null;
  const source = props.head?.kind === "source" ? props.head.source : null;
  return (
    <div className="flex flex-col gap-1.5">
      {specs.map((spec) => (
        <OperandControl
          key={spec.slot}
          ctx={ctx}
          label={spec.label}
          hint={spec.hint}
          required={spec.required(input)}
          operand={block.operands.find((item) => item.slot === spec.slot)}
          source={source}
          onChange={(next) => props.onOperand(spec.slot, next)}
        />
      ))}
      {block.operator === "concat" && <ConcatDiagram side={block.side ?? "append"} />}
    </div>
  );
}

interface OperandSpec {
  readonly slot: number;
  readonly label: string;
  readonly hint?: string;
  readonly required: (input: LogicalType | null) => LogicalType | null;
}

/**
 * The parameter each block asks for, in the IR argument slot it occupies. The slot
 * matters for `concat`: a prepended value is argument 0 and an appended one is
 * argument 1, and that index pair is the only thing that distinguishes them.
 */
export function operandSpecs(block: OperationBlock): OperandSpec[] {
  const str: LogicalType = { kind: "unit", name: "str" };
  const bool: LogicalType = { kind: "unit", name: "bool" };
  const unwrapOrNull = (input: LogicalType | null): LogicalType | null =>
    input == null ? null : input.kind === "nullable" ? input.value : input;
  switch (block.operator) {
    case "coalesce":
      return [{ slot: 1, label: "fallback", hint: "written down — exactly what a missing row becomes", required: unwrapOrNull }];
    case "concat":
      return [
        {
          slot: block.side === "prepend" ? 0 : 1,
          label: block.side === "prepend" ? "in front" : "behind",
          hint: "text, never missing",
          required: () => str,
        },
      ];
    case "join":
      return [{ slot: 1, label: "separator", hint: "written between the items", required: () => str }];
    case "split_before":
    case "split_after":
      return [{ slot: 1, label: "marker", hint: "the text it cuts at", required: () => str }];
    case "replaced":
      return [
        { slot: 1, label: "search", hint: "everywhere it appears", required: () => str },
        { slot: 2, label: "replace with", required: () => str },
      ];
    case "equals":
      return [{ slot: 1, label: "equals", hint: "the text to compare against", required: () => str }];
    case "add":
    case "subtract":
      return [{ slot: 1, label: "operand", hint: "the same number type as the value above", required: unwrapOrNull }];
    case "and":
    case "or":
    case "keep_if":
      return [
        {
          slot: 1,
          label: block.operator === "keep_if" ? "predicate" : "other test",
          hint: "a true-or-false test that is never missing",
          required: () => bool,
        },
      ];
    default:
      return [];
  }
}

function memberOptions(ctx: BindingContext, input: LogicalType | null) {
  const base = input == null ? null : input.kind === "nullable" ? input.value : input;
  const item = base?.kind === "array" ? (base.item.kind === "nullable" ? base.item.value : base.item) : null;
  const struct = base?.kind === "struct" ? base : item?.kind === "struct" ? item : null;
  if (!struct || struct.kind !== "struct") return [];
  return (ctx.document.structs ?? [])
    .filter((entry) => entry.declaration_name === struct.qualname)
    .flatMap((entry) =>
      (entry.fields ?? []).map((field) => ({
        value: field.name,
        label: `${memberNameOf(field.name)}  ·  ${typeLabel(field.logical_type)}`,
      })),
    );
}

/** Which side the written text lands on, drawn as the two arguments it becomes. */
function ConcatDiagram({ side }: { side: "prepend" | "append" }) {
  const box = (name: string, active: boolean) => (
    <span
      className={
        active
          ? "rounded border border-info/50 bg-info/10 px-1 text-ink"
          : "rounded border border-edge px-1 text-muted"
      }
    >
      {name}
    </span>
  );
  return (
    <Tooltip
      content="both authoring methods compile to the operator `concat`; only the order of the two arguments says which was written"
      side="right"
    >
      <span className="flex items-center gap-1 font-mono text-[10px]" aria-label={`the text is written ${side}`}>
        {box(side === "prepend" ? "value" : "stack", true)}
        <span aria-hidden className="text-faint">
          +
        </span>
        {box(side === "prepend" ? "stack" : "value", false)}
        <span aria-hidden className="text-faint">
          →
        </span>
        <span className="rounded border border-edge px-1 text-faint">concat</span>
      </span>
    </Tooltip>
  );
}
