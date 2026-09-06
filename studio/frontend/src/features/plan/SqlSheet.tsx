"use client";

/**
 * The SQL side sheet.
 *
 * Inspecting lowered SQL is a primary reason this view exists, so the text is shown
 * verbatim: a selectable, wrapped `<pre>` — never a syntax-highlighted rewrite that
 * could differ from what the framework will run. The relation name, the step's
 * other payload facts and the connections it sits between are alongside it.
 */

import { useEffect, useRef, useState } from "react";

import { Button, Chip, CloseIcon, IconButton, Panel } from "@/components/ui";
import type { Problem } from "@/lib/types";
import type { StepDetail, StepEdge, StepNode } from "./types";
import { edgeLabel, shorten, stepRef } from "./detail";
import { roleColor } from "./roles";
import { parseRef, refLabel } from "@/lib/ids";
import { ProblemBadge } from "@/components/ui";

export interface SqlSheetProps {
  readonly step: StepNode | null;
  readonly detail: StepDetail | null;
  readonly nodes: readonly StepNode[];
  readonly edges: readonly StepEdge[];
  readonly problems: readonly Problem[];
  readonly onClose: () => void;
  readonly onSelectRef: (ref: string | null) => void;
}

export function SqlSheet({ step, detail, nodes, edges, problems, onClose, onSelectRef }: SqlSheetProps) {
  const [copied, setCopied] = useState(false);
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (copyTimer.current) clearTimeout(copyTimer.current);
  }, []);

  if (!step) return null;
  const sql = step.sql ?? "";
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const incoming = edges.filter((edge) => edge.to_step === step.id);
  const outgoing = edges.filter((edge) => edge.from_step === step.id);
  const ref = stepRef(step);
  const isRef = ref !== null && parseRef(ref) !== null;

  const copy = () => {
    void navigator.clipboard?.writeText(sql).then(
      () => {
        setCopied(true);
        if (copyTimer.current) clearTimeout(copyTimer.current);
        copyTimer.current = setTimeout(() => setCopied(false), 1600);
      },
      () => setCopied(false),
    );
  };

  return (
    <Panel
      role="complementary"
      title="Step payload"
      subtitle={detail?.kindLabel ?? step.kind}
      className="w-[26rem] shrink-0 border-l border-edge"
      bodyClassName="flex flex-col gap-2 overflow-auto"
      actions={
        <>
          {sql.length > 0 && (
            <Button size="sm" onClick={copy} title="Copy the SQL exactly as compiled">
              {copied ? "copied" : "copy"}
            </Button>
          )}
          <IconButton size="sm" label="Close the payload sheet" icon={<CloseIcon size={13} />} onClick={onClose} />
        </>
      }
    >
      <div className="flex flex-col gap-1">
        <p className="break-all font-mono text-[11px] text-ink" data-sql-step={step.id}>
          {step.id}
        </p>
        <div className="flex flex-wrap items-center gap-1">
          <Chip>{step.module_id}</Chip>
          {step.relation && <Chip tone="info" title="DuckDB relation this step defines">{step.relation}</Chip>}
          {step.action && <Chip title="core action">{step.action}</Chip>}
          {(step.notes ?? []).map((note) => (
            <Chip key={note} tone="template" title={note}>
              {shorten(note, 30)}
            </Chip>
          ))}
          {problems.length > 0 && <ProblemBadge problems={problems} ref={ref} />}
        </div>
        {isRef && ref && (
          <button
            type="button"
            onClick={() => onSelectRef(ref)}
            title={`${ref} — select this IR ref everywhere`}
            className="w-full truncate rounded border border-edge bg-raised px-1.5 py-1 text-left font-mono text-[10px] text-info hover:border-info"
          >
            {refLabel(ref)} · {ref}
          </button>
        )}
      </div>

      {sql.length > 0 ? (
        <pre
          data-sql-text="true"
          lang="sql"
          className="max-h-[50vh] select-text overflow-auto whitespace-pre-wrap break-words rounded-md border border-edge bg-canvas p-2 font-mono text-[11px] leading-[1.45] text-ink"
        >
          {sql}
        </pre>
      ) : (
        <p className="rounded-md border border-edge bg-canvas p-2 text-[12px] text-faint">
          This step carries no SQL — its payload is {step.payload_keys?.length ? step.payload_keys.join(", ") : "empty"}.
        </p>
      )}

      {(incoming.length > 0 || outgoing.length > 0) && (
        <div className="flex flex-col gap-1">
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-muted">connections</p>
          <ul className="flex flex-col gap-0.5">
            {incoming.map((edge) => (
              <ConnectionRow key={`in-${edge.id}`} edge={edge} other={byId.get(edge.from_step)?.label ?? edge.from_step} direction="in" />
            ))}
            {outgoing.map((edge) => (
              <ConnectionRow key={`out-${edge.id}`} edge={edge} other={byId.get(edge.to_step)?.label ?? edge.to_step} direction="out" />
            ))}
          </ul>
        </div>
      )}

      {detail && detail.facts.length > 0 && (
        <ul className="flex flex-col gap-0.5 border-t border-edge pt-1.5">
          {detail.facts.map((fact) => (
            <li
              key={fact.text}
              title={fact.title ?? fact.text}
              className="truncate font-mono text-[11px] text-muted"
            >
              {fact.text}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function ConnectionRow({
  edge,
  other,
  direction,
}: {
  edge: StepEdge;
  other: string;
  direction: "in" | "out";
}) {
  const color = roleColor(edge.role ?? null);
  return (
    <li className="flex items-center gap-1.5 font-mono text-[10px] text-muted">
      <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full" style={{ background: color }} />
      <span className="text-faint">{direction === "in" ? "←" : "→"}</span>
      <span className="min-w-0 flex-1 truncate" title={edge.id}>
        {other}
      </span>
      <span className="shrink-0 text-faint">{edgeLabel(edge)}</span>
    </li>
  );
}
