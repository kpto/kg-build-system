"use client";

/**
 * Embed bridge.
 *
 * A host may frame the viewer with `?embed=1`. The host sends one arbitrary
 * snapshot and receives selection events. The viewer never needs to know where
 * the snapshot came from: it accepts a parsed document or raw JSON text.
 */

import { loadSnapshotFromObject, loadSnapshotFromText } from "@/lib/load";
import type { ViewerSnapshot } from "@/lib/types";

import type { SubjectSelection } from "./types";

export const EMBED_QUERY_KEY = "embed";
export const EMBED_QUERY_VALUE = "1";

export interface EmbedQuery {
  enabled: boolean;
  /** Optional URL fallback retained for standalone loads. */
  snapshot?: string;
}

export function embedQuery(search: string): EmbedQuery {
  const params = new URLSearchParams(search);
  return {
    enabled: params.get(EMBED_QUERY_KEY) === EMBED_QUERY_VALUE,
    snapshot: params.get("snapshot") ?? undefined,
  };
}

export interface EmbedReadyMessage {
  type: "ready";
  snapshot?: string;
}

export interface EmbedSelectMessage {
  type: "select";
  subject: SubjectSelection;
}

export interface EmbedErrorMessage {
  type: "error";
  message: string;
}

export type EmbedEvent =
  | EmbedReadyMessage
  | EmbedSelectMessage
  | EmbedErrorMessage;

export interface EmbedOpenMessage {
  type: "open";
  snapshot: unknown;
  label?: string;
  requestId?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

/** Parse a host `open` message. Wrong shapes are ignored, never guessed. */
export function parseOpenMessage(value: unknown): EmbedOpenMessage | null {
  if (!isRecord(value) || value.type !== "open") return null;
  if (!("snapshot" in value)) return null;
  return {
    type: "open",
    snapshot: value.snapshot,
    ...(typeof value.label === "string" ? { label: value.label } : {}),
    ...(typeof value.requestId === "string"
      ? { requestId: value.requestId }
      : {}),
  };
}

/** Normalise the `snapshot` member: raw JSON text or a parsed document. */
export function snapshotFromOpen(value: unknown): ViewerSnapshot {
  if (typeof value === "string") return loadSnapshotFromText(value);
  return loadSnapshotFromObject(value);
}

export function createReadyMessage(snapshot?: string): EmbedReadyMessage {
  return { type: "ready", ...(snapshot ? { snapshot } : {}) };
}

export function createSelectMessage(
  subject: SubjectSelection,
): EmbedSelectMessage {
  return { type: "select", subject };
}

export function createErrorMessage(message: string): EmbedErrorMessage {
  return { type: "error", message };
}

/**
 * The parent origin when the browser exposes it. The iframe may be loaded with
 * `referrerpolicy=no-referrer`, in which case the only safe fallback is `*`;
 * the host validates origin and source itself.
 */
export function parentOrigin(): string {
  if (typeof document === "undefined" || !document.referrer) return "*";
  try {
    return new URL(document.referrer).origin;
  } catch {
    return "*";
  }
}

export function postToParent(event: EmbedEvent): void {
  if (typeof window === "undefined") return;
  if (window.parent === window) return;
  window.parent.postMessage(event, parentOrigin());
}
