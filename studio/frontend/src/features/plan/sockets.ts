/**
 * Socket grouping for a compositor node.
 *
 * A step declares its slots in contract order; the canvas shows every input above
 * every output, one handle each. Slot ids are already step-qualified
 * (`core::binding.0.inputs`), so they double as React Flow handle ids without a
 * second namespace — but they are still de-duplicated here, because a handle id
 * that repeats inside one node makes React Flow resolve edges to the wrong row.
 */

import type { StepNode, Socket, SocketGroup } from "./types";
import { roleLabel } from "./roles";

/** The last dotted component of a slot id — `core::table.sites.output` → `output`. */
export function slotName(slotId: string): string {
  const local = slotId.includes("::") ? slotId.slice(slotId.indexOf("::") + 2) : slotId;
  const dot = local.lastIndexOf(".");
  return dot < 0 ? local : local.slice(dot + 1);
}

function toSocket(
  slot: { readonly slot_id: string; readonly role?: string | null; readonly ref?: string | null },
  isOutput: boolean,
): Socket {
  const role = slot.role ?? null;
  return {
    id: slot.slot_id,
    slotId: slot.slot_id,
    label: isOutput && role ? roleLabel(role) : slotName(slot.slot_id),
    role: isOutput ? role : null,
    ref: slot.ref ?? null,
  };
}

/** Inputs above outputs, each de-duplicated by slot id in first-seen order. */
export function groupSockets(node: StepNode): SocketGroup {
  return {
    inputs: unique(node.inputs ?? [])
      .map((slot) => toSocket(slot, false))
      .sort((a, b) => (a.slotId < b.slotId ? -1 : a.slotId > b.slotId ? 1 : 0)),
    outputs: unique(node.outputs ?? [])
      .map((slot) => toSocket(slot, true))
      .sort((a, b) => (a.slotId < b.slotId ? -1 : a.slotId > b.slotId ? 1 : 0)),
  };
}

type RawSlot = { readonly slot_id: string; readonly role?: string | null; readonly ref?: string | null };

function unique(slots: readonly RawSlot[]): readonly RawSlot[] {
  const seen = new Set<string>();
  const out: RawSlot[] = [];
  for (const slot of slots) {
    if (seen.has(slot.slot_id)) continue;
    seen.add(slot.slot_id);
    out.push({ slot_id: slot.slot_id, role: slot.role ?? null, ref: slot.ref ?? null });
  }
  return out;
}

