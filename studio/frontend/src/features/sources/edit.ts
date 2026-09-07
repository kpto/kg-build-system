/**
 * Document edits for the Sources area. As in `contracts/edit.ts`, every function is a
 * `(draft) => draft` rebuilder handed straight to `apply(...)`, so a delete is an
 * ordinary document edit and rides the store's undo stack like any other change.
 */

import { buildRef } from "@/lib/ids";
import { removed, type ProjectDocument } from "@/lib/ir";

/**
 * Remove one `bind_source`, leaving the table it fed alone.
 *
 * Nothing in the document stores a pointer to a source — the reference runs source →
 * table, and the table's own shape is its own declaration — so there is no field here
 * to repoint, and the two things that must not happen are enforced elsewhere and here:
 * `referrersOfSource` blocks the delete while a binding or projection still reads a
 * table this source was feeding, and this function touches nothing but the source.
 * Dropping the table with it would delete columns the author wrote to destroy work
 * nobody asked to destroy; leaving one behind unbound is the repairable state the
 * Sources tab already lists under "missing".
 *
 * The one stored thing keyed by a source's ref is its canvas position, so that goes
 * with it, as `removeComponentCascade` does for a component.
 */
export function removeSourceCascade(document: ProjectDocument, sourceId: string): ProjectDocument {
  const ref = buildRef("source", sourceId);
  const topology = document.views?.topology;
  if (!topology || !(ref in topology)) return removed(document, "sources", sourceId);
  const positions = { ...topology };
  delete positions[ref];
  return { ...removed(document, "sources", sourceId), views: { ...document.views, topology: positions } };
}
