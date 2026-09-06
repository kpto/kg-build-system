"use client";

/**
 * The generated-code preview.
 *
 * A local renderer (`logic/preview.ts`) over the expression tree, so the author reads
 * the authoring Python their stack means and learns the DSL. It is labelled a preview
 * everywhere: the backend generator is the authority for the file, its imports and its
 * anchors, and this panel shows none of them.
 */

import { useState } from "react";

import { ChevronIcon } from "@/components/ui";
import type { Expression } from "@/lib/ir";
import type { BindingContext } from "../logic/context";
import { renderPreview } from "../logic/preview";

export interface PreviewPanelProps {
  ctx: BindingContext;
  expression: Expression | null;
  /** The stack's IR ref, so the author can see which slot this code belongs to. */
  stackRef: string;
}

export function PreviewPanel({ ctx, expression, stackRef }: PreviewPanelProps) {
  const [open, setOpen] = useState(true);
  const code = expression ? renderPreview(ctx, expression) : "";

  return (
    <footer className="shrink-0 border-t border-edge bg-canvas">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex h-7 w-full items-center gap-1.5 px-2.5 text-[11px] text-muted hover:text-ink"
      >
        <ChevronIcon size={12} open={open} />
        <span className="font-medium">authoring Python</span>
        <span className="rounded border border-edge bg-raised px-1 font-mono text-[9px] text-faint">preview</span>
        <span className="truncate font-mono text-[10px] text-faint">{stackRef}</span>
        <span className="ml-auto shrink-0 text-[10px] text-faint">the backend generator stays authoritative</span>
      </button>
      {open && (
        <pre className="max-h-32 overflow-auto px-3 pb-2 font-mono text-[11px] leading-relaxed text-relation">
          {code.length > 0 ? code : "— nothing to render yet —"}
        </pre>
      )}
    </footer>
  );
}
