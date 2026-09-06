/**
 * Deterministic node sizing.
 *
 * The layout must know a node's box *before* the DOM exists (that is the only way
 * it can be pure, testable and overlap-free), so the height is computed from the
 * content the card will render and the card is then rendered at exactly that box.
 * One place owns the numbers; `StepNode.tsx` uses the same constants.
 */

import type { StepDetail, StepNode } from "./types";
import type { SocketGroup } from "./types";
import { groupSockets } from "./sockets";
import { STEP_WIDTH } from "./StepNode";
import type { StepSize } from "./layout";

export const HEADER_HEIGHT = 22;
export const META_HEIGHT = 12;
export const SUMMARY_HEIGHT = 13;
export const SOCKET_HEIGHT = 16;
export const SOCKET_GAP = 2;
export const FACT_HEIGHT = 13;
export const BADGE_HEIGHT = 17;
export const BODY_PADDING = 8;
export const DIVIDER = 1;
export const MAX_FACT_LINES = 3;

export interface StepContent {
  readonly sockets: SocketGroup;
  readonly summary: boolean;
  readonly factLines: number;
  readonly badgeLines: number;
}

/** The rows a card will show — the whole basis of its height. */
export function stepContent(node: StepNode, detail: StepDetail): StepContent {
  const sockets = groupSockets(node);
  const badges = detail.badges.length;
  return {
    sockets,
    summary: detail.summary !== null && detail.summary.length > 0,
    factLines: Math.min(detail.facts.length, MAX_FACT_LINES),
    badgeLines: badges > 0 ? Math.min(Math.ceil(badges / 2), 2) : 0,
  };
}

export function estimateStepHeight(content: StepContent): number {
  const socketRows = content.sockets.inputs.length + content.sockets.outputs.length;
  let height = HEADER_HEIGHT + BODY_PADDING + META_HEIGHT;
  if (content.summary) height += SUMMARY_HEIGHT;
  if (socketRows > 0) {
    height += socketRows * SOCKET_HEIGHT + Math.max(0, socketRows - 1) * SOCKET_GAP + DIVIDER;
  }
  if (content.factLines > 0) height += content.factLines * FACT_HEIGHT;
  if (content.badgeLines > 0) height += content.badgeLines * BADGE_HEIGHT;
  return Math.max(56, Math.round(height));
}

/** `id → box` for every step, at the fixed card width. */
export function measureSteps(
  nodes: readonly StepNode[],
  details: ReadonlyMap<string, StepDetail>,
): Map<string, StepSize> {
  const sizes = new Map<string, StepSize>();
  for (const node of nodes) {
    const detail = details.get(node.id);
    const content = stepContent(node, detail ?? EMPTY_DETAIL);
    sizes.set(node.id, { width: STEP_WIDTH, height: estimateStepHeight(content) });
  }
  return sizes;
}

const EMPTY_DETAIL: StepDetail = {
  kindLabel: "step",
  summary: null,
  facts: [],
  badges: [],
  hasSql: false,
  relation: null,
  location: null,
  target: null,
};
