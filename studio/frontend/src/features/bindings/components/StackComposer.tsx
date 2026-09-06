"use client";

/**
 * The stack composer — DESIGN.md §5's vertical chain of blocks.
 *
 * It owns no state the document does not: the stack *is* the expression at the
 * selected ref, decomposed on render and recomposed on every edit, and every edit
 * leaves through `apply`. The local state is only view state (which menu is open,
 * which deletion was asked for, whether the drag was refused).
 */

import { useMemo, useState } from "react";

import { DndContext, KeyboardSensor, PointerSensor, closestCenter, useSensor, useSensors } from "@dnd-kit/core";
import type { DragEndEvent } from "@dnd-kit/core";
import { SortableContext, arrayMove, sortableKeyboardCoordinates, verticalListSortingStrategy } from "@dnd-kit/sortable";

import { Chip, ProblemBadge } from "@/components/ui";
import type { Binding, Expression, LogicalType, ProjectDocument } from "@/lib/ir";
import { typeLabel } from "@/lib/ir";
import type { OperatorEntry, Problem, ResolvedProperty } from "@/lib/types";
import type { BindingContext } from "../logic/context";
import {
  blocksFromExpression,
  expressionFromBlocks,
  labelFor,
  moveBlocks,
  removeBlock,
  reseatHead,
  seamsFor,
  type Block,
  type OperationBlock,
  type Operand,
} from "../logic/stack";
import { blockFor, headsFor, paletteFor, type PaletteEntry } from "../logic/palette";
import { checkKey, checkSlot, type HeadTarget } from "../logic/rules";
import { renderPreview } from "../logic/preview";
import { expressionAt, stackRef, withStackExpression, withoutProperty, type StackTarget } from "../logic/edits";
import { BlockCard } from "./BlockCard";
import { AddBlockButton, AddBlockMenu } from "./AddBlockMenu";
import { PreviewPanel } from "./PreviewPanel";

export interface StackComposerProps {
  ctx: BindingContext;
  binding: Binding;
  target: StackTarget;
  slot: ResolvedProperty | null;
  componentName: string;
  operators: readonly OperatorEntry[];
  problems: readonly Problem[];
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
}

export function StackComposer(props: StackComposerProps) {
  const { ctx, binding, target, slot, componentName, operators, problems } = props;
  const [menuOpen, setMenuOpen] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<number | null>(null);

  const ref = stackRef(binding.id, target);
  const expression = expressionAt(binding, target);
  const blocks = useMemo(() => blocksFromExpression(expression), [expression]);
  const seams = useMemo(() => seamsFor(ctx, blocks), [ctx, blocks]);
  const tip = seams.types[seams.types.length - 1] ?? null;
  const steps = useMemo(() => paletteFor(ctx, operators, tip), [ctx, operators, tip]);
  const headTarget = useMemo<HeadTarget>(
    () => ({ componentName, slot, key: target.part === "property" ? null : target.part }),
    [componentName, slot, target.part],
  );
  // An empty stack has no tip to filter the catalogue against, so its palette starts the
  // stack: the heads that can fill this slot or key, ahead of the operations they unlock.
  const palette = useMemo(
    () => (blocks.length === 0 ? [...headsFor(ctx, headTarget), ...steps] : steps),
    [blocks.length, ctx, headTarget, steps],
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  /** One place every edit lands: rebuild the stack, then rebuild the document. */
  function commit(next: readonly Block[], note?: string) {
    const built = expressionFromBlocks(ctx, next);
    if (!built.expression) {
      setNotice(built.error ?? "that stack does not resolve yet");
      return;
    }
    setNotice(note ?? null);
    props.apply((draft) => withStackExpression(draft, binding.id, target, built.expression as Expression));
  }

  /* ------------------------------------------------------------------ block edits */

  // Re-pointing the head changes what every block below receives, so the blocks the
  // framework would now reject go with it — and the composer says how many.
  function reseat(head: Block) {
    const next = reseatHead(ctx, blocks, head);
    commit(
      next.blocks,
      next.dropped.length > 0
        ? `the new source does not fit ${next.dropped.length} block${next.dropped.length === 1 ? "" : "s"} — ${next.dropped.map((block) => labelFor(block)).join(", ")} removed`
        : undefined,
    );
  }

  function selectSource(source: string) {
    const head = blocks[0];
    if (head?.kind !== "source") return;
    reseat({ ...head, source, path: [] });
  }

  function selectPath(path: readonly string[]) {
    const head = blocks[0];
    if (head?.kind !== "source") return;
    reseat({ ...head, path });
  }

  function pick(entry: PaletteEntry) {
    // A head is only offered while the stack is empty, and the head is the whole stack;
    // it leaves through `commit` like every other edit, so it is undoable like them too.
    if (entry.head) {
      commit([blockFor(entry, tip)]);
      setMenuOpen(false);
      return;
    }
    // A member read off a plain field reference is folded into that reference's path,
    // because that is what the framework compiles it to. It only becomes a
    // `struct_field` block once an operation sits underneath.
    if (entry.operator === "struct_field" && blocks.every((block) => block.role === "head")) {
      const head = blocks[0];
      const members = membersOf(ctx, tip);
      const first = members[0];
      if (head?.kind === "source" && first) {
        commit([{ ...head, path: [...head.path, first] }], "folded into the field path — a pick on a field reference records no node");
        setMenuOpen(false);
        return;
      }
    }
    const member = entry.operator === "struct_field" || entry.operator === "map_items" ? membersOf(ctx, tip)[0] : undefined;
    commit([...blocks, blockFor(entry, tip, member ? { member } : {})]);
    setMenuOpen(false);
  }

  function renameMember(block: OperationBlock, name: string) {
    commit(blocks.map((item) => (item.id === block.id ? { ...block, parameters: { ...block.parameters, name } } : item)));
  }

  function setOperand(block: OperationBlock, slotIndex: number, operand: Operand) {
    const operands = [...block.operands.filter((item) => item.slot !== slotIndex), { ...operand, slot: slotIndex }];
    commit(blocks.map((item) => (item.id === block.id ? { ...block, operands } : item)));
  }

  function askDelete(index: number) {
    if (pendingDelete === index) {
      const { blocks: next, removed } = removeBlock(ctx, blocks, index);
      commit(next, removed.length > 1 ? `removed ${removed.length} blocks — the ones below needed this one` : undefined);
      setPendingDelete(null);
      return;
    }
    setPendingDelete(index);
  }

  function onDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const from = blocks.findIndex((block) => block.id === active.id);
    const to = blocks.findIndex((block) => block.id === over.id);
    const moved = moveBlocks(ctx, blocks, from, to);
    if (moved.reason) {
      setNotice(moved.reason);
      return;
    }
    setNotice(null);
    commit(moved.blocks);
  }

  /* -------------------------------------------------------------------- reporting */

  const keyCheck = target.part === "property" ? null : checkKey(target.part, tip);
  const slotCheck = target.part === "property" ? checkSlot(componentName, slot, tip) : null;
  const canDeleteProperty = target.part === "property" && (slot?.optional ?? false);
  const downstreamOf = (index: number) => removeBlock(ctx, blocks, index).removed.length - (blocks[index]?.role === "step" ? 1 : 0);

  return (
    <section className="relative flex min-h-0 flex-1 flex-col bg-surface" aria-label={`stack for ${ref}`}>
      <header className="flex min-h-9 shrink-0 flex-wrap items-center gap-2 border-b border-edge px-2.5 py-1">
        <h2 className="truncate font-mono text-[12px] text-ink">{label(ref)}</h2>
        {slot ? (
          <Chip tone={slotCheck?.ok ? "ok" : "danger"} title={`the component declares ${typeLabel(slot.logical_type)}`}>
            expects {typeLabel(slot.logical_type)}
            {slot.optional ? " (optional)" : ""}
          </Chip>
        ) : (
          <Chip tone={keyCheck?.ok ? "ok" : "danger"} title="a key must be a non-null scalar">
            key · non-null scalar
          </Chip>
        )}
        <span className="ml-auto flex items-center gap-1.5">
          <ProblemBadge problems={problems} ref={ref} />
          {canDeleteProperty && (
            <button
              type="button"
              onClick={() => props.apply((draft) => withoutProperty(draft, binding.id, (target as { name: string }).name))}
              className="rounded border border-edge px-1.5 py-0.5 text-[10px] text-muted hover:border-danger hover:text-danger"
              title="leave this optional slot unbound — the record defaults it to a typed null"
            >
              unbind
            </button>
          )}
        </span>
      </header>

      {notice && (
        <p className="flex shrink-0 items-center gap-2 border-b border-edge bg-raised px-2.5 py-1 text-[11px] text-info">
          {notice}
          <button type="button" onClick={() => setNotice(null)} aria-label="Dismiss" className="ml-auto text-faint hover:text-ink">
            ×
          </button>
        </p>
      )}

      {keyCheck && !keyCheck.ok && (
        <Mismatch
          tone="danger"
          headline={keyCheck.message ?? "this key is not valid"}
          detail={`the stack produces ${tip == null ? "nothing yet" : typeLabel(tip)}`}
          action={
            keyCheck.fix === "where_present"
              ? {
                  label: "insert Keep rows where present",
                  run: () => {
                    const entry = palette.find((item) => item.operator === "where_present");
                    if (entry) commit([...blocks, blockFor(entry, tip)]);
                  },
                }
              : undefined
          }
        />
      )}

      {slotCheck && !slotCheck.ok && (
        <Mismatch
          tone="danger"
          headline={slotCheck.message ?? ""}
          detail={`expects ${slot ? typeLabel(slot.logical_type) : "?"}, got ${tip == null ? "nothing yet" : typeLabel(tip)}${
            slotCheck.hint ? ` · ${slotCheck.hint}` : ""
          }`}
        />
      )}

      {seams.broken && (
        <Mismatch
          tone="warn"
          headline={`${labelFor(blocks[seams.broken.index])} does not fit the value above it`}
          detail={seams.broken.message}
        />
      )}

      <div className="min-h-0 flex-1 overflow-auto p-2 pb-14">
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
          <SortableContext items={blocks.map((block) => block.id)} strategy={verticalListSortingStrategy}>
            <ul className="flex flex-col">
              {blocks.map((block, index) => (
                <BlockCard
                  key={block.id}
                  ctx={ctx}
                  block={block}
                  index={index}
                  count={blocks.length}
                  head={blocks[0]}
                  input={index === 0 ? null : (seams.types[index - 1] ?? null)}
                  output={seams.types[index] ?? null}
                  operator={operators.find((entry) => entry.operator === (block.kind === "operation" ? block.operator : ""))}
                  downstream={block.role === "step" ? Math.max(0, downstreamOf(index)) : 0}
                  onSelectSource={selectSource}
                  onSelectPath={selectPath}
                  onRenameMember={(name) => block.kind === "operation" && renameMember(block, name)}
                  onOperand={(slotIndex, operand) => block.kind === "operation" && setOperand(block, slotIndex, operand)}
                  onDelete={askDelete}
                  pendingDelete={pendingDelete === index}
                />
              ))}
            </ul>
          </SortableContext>
        </DndContext>

        {blocks.length === 0 && (
          <p className="p-2 text-[12px] text-muted">
            {target.part === "property"
              ? "this slot is unfilled — pick a source to start its stack."
              : "this key has no expression yet."}
          </p>
        )}

        <div className="mt-1 pl-3">
          <AddBlockButton onClick={() => setMenuOpen(true)} empty={blocks.length === 0} tip={tip} />
        </div>

        {pendingDelete !== null && (
          <p className="mt-2 flex items-center gap-2 rounded-md border border-warn/50 bg-warn/10 px-2 py-1 text-[11px] text-warn">
            remove {labelFor(blocks[pendingDelete])}?
            {downstreamOf(pendingDelete) > 0 &&
              ` this also removes ${downstreamOf(pendingDelete)} downstream block${downstreamOf(pendingDelete) === 1 ? "" : "s"}`}
            <button type="button" onClick={() => setPendingDelete(null)} className="ml-auto text-muted hover:text-ink">
              cancel
            </button>
          </p>
        )}
      </div>

      {menuOpen && (
        <AddBlockMenu
          ctx={ctx}
          entries={palette}
          tip={tip}
          onPick={pick}
          onFix={(entry) => {
            const fix = palette.find((item) => item.operator === entry.fix?.operator);
            if (fix) commit([...blocks, blockFor(fix, tip)]);
            setMenuOpen(false);
          }}
          onClose={() => setMenuOpen(false)}
        />
      )}

      <PreviewPanel expression={expression} ctx={ctx} stackRef={ref} />
    </section>
  );
}

function membersOf(ctx: BindingContext, type: LogicalType | null): string[] {
  if (type == null) return [];
  const base = type.kind === "nullable" ? type.value : type;
  const struct = base.kind === "struct" ? base : base.kind === "array" ? (base.item.kind === "nullable" ? base.item.value : base.item) : null;
  if (!struct || struct.kind !== "struct") return [];
  return (ctx.document.structs ?? [])
    .find((item) => item.declaration_name === struct.qualname)
    ?.fields?.map((field) => field.name) ?? [];
}

const label = (ref: string) => ref.replace(/^binding:/, "").replace(".property.", " · ");

function Mismatch({
  tone,
  headline,
  detail,
  action,
}: {
  tone: "danger" | "warn";
  headline: string;
  detail?: string;
  action?: { label: string; run(): void };
}) {
  const classes =
    tone === "danger"
      ? "border-danger/60 bg-danger/10 text-danger"
      : "border-warn/60 bg-warn/10 text-warn";
  return (
    <div role="alert" className={`flex shrink-0 flex-wrap items-center gap-2 border-b px-2.5 py-1.5 text-[11px] ${classes} ${tone === "danger" ? "" : ""}`}>
      <span className="font-medium">{headline}</span>
      {detail && <span className="font-mono text-[10px] opacity-90">{detail}</span>}
      {action && (
        <button
          type="button"
          onClick={action.run}
          className="ml-auto rounded border border-current px-1.5 py-0.5 text-[10px] hover:bg-current/10"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
