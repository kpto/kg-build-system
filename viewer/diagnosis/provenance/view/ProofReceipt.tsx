"use client";

import type { KeyboardEvent, ReactNode } from "react";
import { MousePointerClick } from "lucide-react";
import { cx } from "@/shared/ui/theme";
import type {
  ProvenanceReceiptFieldModel,
  ProvenanceReceiptModel,
  ProvenanceReceiptRowModel,
} from "@/diagnosis/provenance/model/ProvenanceModel";
import { ExpressionSyntax } from "@/diagnosis/provenance/view/ExpressionSyntax";

function ReceiptField({
  field,
  children,
}: {
  field: ProvenanceReceiptFieldModel;
  children?: ReactNode;
}) {
  const tone =
    field.tone === "source"
      ? "text-source"
      : field.tone === "target"
        ? "text-target"
        : field.tone === "faint"
          ? "text-faint"
          : undefined;
  return (
    <span data-level="field" className="ui-field min-w-0 px-0 py-0">
      <span className="ui-field-label">{field.label}</span>
      <span className={cx("ui-field-value break-words", tone)} title={field.title}>
        {children ?? field.value}
      </span>
    </span>
  );
}

function ReceiptRow({ row }: { row: ProvenanceReceiptRowModel }) {
  const focus = () => row.focus?.run();

  return (
    <li
      role="button"
      tabIndex={0}
      data-testid={`receipt-step-${row.index}`}
      data-level="row"
      data-selected={row.selected ? "true" : "false"}
      aria-pressed={row.selected}
      onClick={focus}
      onKeyDown={(event: KeyboardEvent<HTMLLIElement>) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          focus();
        }
      }}
      title={row.title}
      className="ui-row group/proof cursor-pointer items-start py-1"
    >
      <span
        className={cx(
          "mt-0.5 inline-flex size-4 shrink-0 items-center justify-center rounded-[2px] border font-mono text-[8.5px] tnum",
          row.selected
            ? "border-accent/40 bg-accent/10 text-accent"
            : "border-line-soft bg-panel-soft/40 text-faint",
        )}
      >
        {row.ordinal}
      </span>

      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="flex min-w-0 items-center gap-2">
          <span className="ui-section-count shrink-0">
            branch {row.index + 1}
          </span>
          <span className="min-w-0 truncate font-mono text-[10px] text-text">
            {row.propertyName}
          </span>
          <span className="ui-chip shrink-0 text-[10px] text-accent">
            binding #{row.bindingIndex}
          </span>
          <span
            className={cx(
              "ml-auto shrink-0 font-mono text-[8px] uppercase tracking-[0.1em] transition",
              row.selected
                ? "text-accent"
                : "text-faint opacity-0 group-hover/proof:opacity-100 group-focus-visible/proof:opacity-100",
            )}
          >
            {row.selected ? "focused" : "focus →"}
          </span>
        </span>

        <span className="grid min-w-0 grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-2">
          <ReceiptField field={row.source}>
            <span className="text-source">{row.source.value}</span>
          </ReceiptField>
          <ReceiptField field={row.operator}>
            {row.operator.expression ? (
              <ExpressionSyntax expression={row.operator.expression} />
            ) : (
              <span className="text-faint">direct copy</span>
            )}
          </ReceiptField>
          <ReceiptField field={row.binding} />
          <ReceiptField field={row.target}>
            {row.target.tone === "target" ? (
              <span className="text-target">{row.target.value}</span>
            ) : (
              <span className="text-faint">{row.target.value}</span>
            )}
          </ReceiptField>
        </span>

        <span className="ui-row-meta flex min-w-0 flex-wrap gap-x-2">
          <span>
            post{" "}
            <span className="text-post">
              aggregate{" "}
              <span className="text-muted">
                {row.aggregates.join(", ") || "none"}
              </span>
            </span>
            <span className="mx-1 text-line">·</span>
            <span className="text-post">
              dedup{" "}
              <span className="text-muted">
                {row.dedups.join(", ") || "none"}
              </span>
            </span>
          </span>
          {row.operators.length ? (
            <span className="truncate">
              operators{" "}
              <span className="text-accent">{row.operators.join(" → ")}</span>
            </span>
          ) : null}
          <span className="min-w-0 truncate" title={row.identity}>
            identity <span className="text-muted">{row.identity}</span>
          </span>
        </span>
      </span>
    </li>
  );
}

export interface ProofReceiptProps {
  model: ProvenanceReceiptModel;
}

/**
 * Plain-language proof receipt for every branch of a property lineage.
 *
 * The receipt is a row group inside the Lineage inspector section: one branch
 * per row, with the branch chain rendered as inset fields
 * (`source → operator → binding → target`). Activating a row focuses its
 * binding node on the canvas; the row uses the blue list-selection state, while
 * the canvas node remains orange.
 */
export function ProofReceipt({ model }: ProofReceiptProps) {
  return (
    <div
      data-testid="proof-receipt"
      data-level="section"
      role="region"
      aria-label={model.question}
      className="ui-section min-w-0"
    >
      <div className="ui-section-header">
        <h3 className="ui-section-title shrink-0">{model.title}</h3>
        <span className="ui-section-count shrink-0">{model.countLabel}</span>
        <span className="ui-row-meta hidden min-w-0 truncate sm:inline">
          {model.schemaLabel}
        </span>
        <span
          data-testid="proof-receipt-focus-hint"
          className="ui-chip ml-auto shrink-0 gap-1 text-[10px] text-accent"
        >
          <MousePointerClick className="size-2.5" aria-hidden />
          {model.hint}
        </span>
      </div>

      <ol>
        {model.rows.map((row) => (
          <ReceiptRow key={row.id} row={row} />
        ))}
        {!model.rows.length ? (
          <li className="ui-row text-faint">
            <span className="ui-row-meta">{model.emptyHint}</span>
          </li>
        ) : null}
      </ol>
    </div>
  );
}
