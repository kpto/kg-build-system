"use client";

/**
 * The one-line legend under the canvas: what an edge colour means and what the
 * socket rows are, so the first read of the graph does not depend on knowing the
 * framework's artifact-role vocabulary.
 */

import { TOKEN } from "./tokens";
import { ROLE_LABEL, type RoleFamily } from "./roles";

const ORDER: readonly RoleFamily[] = ["table", "projection", "binding", "node", "edge", "publication"];

const SWATCH: Record<RoleFamily, string> = {
  table: TOKEN.template,
  projection: TOKEN.edgekind,
  binding: TOKEN.category,
  node: TOKEN.node,
  edge: TOKEN.relation,
  publication: TOKEN.warn,
  other: TOKEN.faint,
};

export function Legend() {
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-1 border-t border-edge bg-surface px-2.5 py-1 font-mono text-[10px] text-faint">
      <span className="uppercase tracking-[0.08em]">artifact roles</span>
      {ORDER.map((family) => (
        <span key={family} className="flex items-center gap-1">
          <span aria-hidden className="h-px w-4" style={{ background: SWATCH[family] }} />
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: SWATCH[family] }} />
          {ROLE_LABEL[family]}
        </span>
      ))}
      <span aria-hidden className="h-3 w-px bg-edge" />
      <span>sockets: inputs above outputs</span>
      <span aria-hidden className="h-3 w-px bg-edge" />
      <span>{"{ }"} opens the step&apos;s lowered SQL</span>
    </div>
  );
}
