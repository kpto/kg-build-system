/**
 * Sub-DAG tracing for cross-highlighting.
 *
 * Hovering a node lights the whole chain that step belongs to: everything that
 * feeds it and everything it feeds. Both walks are visited-set bounded, so a plan
 * that somehow arrives cyclic still terminates (the layout drops the back edge, but
 * highlighting follows the data as declared).
 */

import type { StepEdge } from "./types";

export interface Trace {
  readonly ancestors: ReadonlySet<string>;
  readonly descendants: ReadonlySet<string>;
  readonly related: ReadonlySet<string>;
  readonly relatedEdges: ReadonlySet<string>;
}

function walk(start: string, adjacency: ReadonlyMap<string, readonly string[]>): Set<string> {
  const seen = new Set<string>();
  const queue = [start];
  while (queue.length > 0) {
    const id = queue.shift() as string;
    for (const next of adjacency.get(id) ?? []) {
      if (seen.has(next) || next === start) continue;
      seen.add(next);
      queue.push(next);
    }
  }
  return seen;
}

/** Everything upstream/downstream of `focus`, plus the edges that carry it. */
export function traceSubDag(
  focus: string | null,
  nodes: readonly { readonly id: string }[],
  edges: readonly StepEdge[],
): Trace {
  if (!focus) {
    return { ancestors: new Set(), descendants: new Set(), related: new Set(), relatedEdges: new Set() };
  }
  const parents = new Map<string, string[]>();
  const children = new Map<string, string[]>();
  for (const node of nodes) {
    parents.set(node.id, []);
    children.set(node.id, []);
  }
  for (const edge of edges) {
    const to = children.get(edge.from_step);
    if (to) to.push(edge.to_step);
    const from = parents.get(edge.to_step);
    if (from) from.push(edge.from_step);
  }

  const ancestors = walk(focus, parents);
  const descendants = walk(focus, children);
  const related = new Set<string>([focus, ...ancestors, ...descendants]);
  const relatedEdges = new Set<string>();
  for (const edge of edges) {
    if (!related.has(edge.from_step) || !related.has(edge.to_step)) continue;
    // An edge belongs to the sub-DAG only when it is on a path through `focus`:
    // either it enters the ancestor side, or it leaves the descendant side.
    const feedsFocus = edge.to_step === focus || ancestors.has(edge.to_step);
    const fedByFocus = edge.from_step === focus || descendants.has(edge.from_step);
    if (feedsFocus || fedByFocus) relatedEdges.add(edge.id);
  }

  return { ancestors, descendants, related, relatedEdges };
}
