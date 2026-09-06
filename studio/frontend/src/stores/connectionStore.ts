/**
 * Connection store: the WebSocket state, the backend status model and the notices
 * raised by writes and events.
 *
 * The header's status light is derived from `StatusModel` alone (API.md), so the
 * whole tool's colour comes from one place and cannot disagree with a panel.
 */

import { create } from "zustand";

import type { GenerationState, Notice, StatusModel, WsEventType } from "@/lib/types";

export type SocketState = "connecting" | "open" | "closed" | "error" | "off";

/** The header light's four states; `unknown` means "we have nothing to say". */
export type StatusLevel = "ok" | "warn" | "error" | "unknown";

export interface ConnectionState {
  socket: SocketState;
  /** Monotonic, so the UI can show "reconnected ×3" without keeping history. */
  reconnects: number;
  lastEventAt: number | null;
  lastEventType: WsEventType | "resync" | "unknown" | null;
  /** Unknown event names seen this session; surfaced in the status tooltip. */
  unknownEvents: string[];
  status: StatusModel | null;
  /** Generation state from `generation` events, which arrive ahead of `status`. */
  generation: GenerationState | null;
  notices: Notice[];

  setSocket(state: SocketState): void;
  setStatus(status: StatusModel | null): void;
  setGeneration(state: GenerationState | null): void;
  noteEvent(type: WsEventType | "resync" | "unknown", name?: string): void;
  notice(input: { level: Notice["level"]; text: string }): void;
  dismissNotice(id: string): void;
  clearNotices(): void;
}

let noticeSeq = 0;

/** The stack is short on purpose; these are acknowledgements, not a log. */
const NOTICE_LIMIT = 6;

/**
 * How long each level stays before it retires itself. Notices float over the canvas
 * and swallow clicks on whatever is underneath them, so a confirmation that outlives
 * the moment it confirms is an obstruction; an error stays until it is acknowledged
 * because it is the only notice of the four that means "look at this".
 */
const NOTICE_LIFETIME: Record<Notice["level"], number | null> = {
  info: 6_000,
  warn: 12_000,
  error: null,
};

const noticeTimers = new Map<string, ReturnType<typeof setTimeout>>();

function clearNoticeTimer(id: string): void {
  const timer = noticeTimers.get(id);
  if (timer !== undefined) {
    clearTimeout(timer);
    noticeTimers.delete(id);
  }
}

export const useConnectionStore = create<ConnectionState>((set, get) => ({
  socket: "off",
  reconnects: 0,
  lastEventAt: null,
  lastEventType: null,
  unknownEvents: [],
  status: null,
  generation: null,
  notices: [],

  setSocket(state) {
    set((current) => ({
      socket: state,
      reconnects:
        state === "open" && current.socket !== "off" && current.socket !== "connecting"
          ? current.reconnects + 1
          : current.reconnects,
    }));
  },

  setStatus(status) {
    set((current) => ({
      status,
      generation: status?.generation?.state ?? current.generation,
    }));
  },

  setGeneration(state) {
    set({ generation: state });
  },

  noteEvent(type, name) {
    set((current) => ({
      lastEventAt: Date.now(),
      lastEventType: type,
      unknownEvents:
        type === "unknown" && name && !current.unknownEvents.includes(name)
          ? [...current.unknownEvents, name].slice(-12)
          : current.unknownEvents,
    }));
  },

  notice({ level, text }) {
    noticeSeq += 1;
    const id = `n${noticeSeq}`;
    const item: Notice = { id, level, text, at: Date.now() };
    set((current) => ({ notices: [...current.notices, item].slice(-NOTICE_LIMIT) }));
    const lifetime = NOTICE_LIFETIME[level];
    if (lifetime !== null) {
      noticeTimers.set(
        id,
        setTimeout(() => {
          noticeTimers.delete(id);
          get().dismissNotice(id);
        }, lifetime),
      );
    }
  },

  dismissNotice(id) {
    clearNoticeTimer(id);
    set((current) => ({ notices: current.notices.filter((item) => item.id !== id) }));
  },

  clearNotices() {
    for (const id of noticeTimers.keys()) clearNoticeTimer(id);
    set({ notices: [] });
  },
}));

/** Imperative helper so non-store modules (ws, api glue) can raise a notice. */
export function notify(input: { level: Notice["level"]; text: string }): void {
  useConnectionStore.getState().notice(input);
}

/* ----------------------------------------------------------------- status light */

export interface StatusLight {
  level: StatusLevel;
  label: string;
  /** One line per tier, for the header tooltip. */
  lines: string[];
  counts: { errors: number; warnings: number };
}

const GENERATION_LABEL: Record<GenerationState, string> = {
  clean: "generation clean",
  dirty: "generation dirty",
  running: "generating",
  done: "generated",
  failed: "generation failed",
  never: "never generated",
};

/**
 * Any error ⇒ red. Otherwise a dirty/running/failed generation ⇒ amber. Otherwise
 * green. A missing status model (no backend) is grey/unknown rather than green, so
 * the light never lies.
 */
export function statusLight(
  status: StatusModel | null,
  overrides?: { generation?: GenerationState | null; dirty?: boolean },
): StatusLight {
  const types = status?.types;
  const blueprint = status?.blueprint;
  const build = status?.build?.state ?? "never";
  const generation = overrides?.generation ?? status?.generation?.state ?? "never";

  const typeErrors = types?.errors ?? 0;
  const typeWarnings = types?.warnings ?? 0;
  const blueprintErrors = blueprint && !blueprint.ok ? (blueprint.errors ?? 0) : 0;
  const buildErrors = build === "failed" ? 1 : 0;
  const errors = typeErrors + blueprintErrors + buildErrors;
  const warnings = typeWarnings;

  const lines: string[] = [];
  if (status) {
    lines.push(`types: ${typeErrors} error${typeErrors === 1 ? "" : "s"}, ${typeWarnings} warning${typeWarnings === 1 ? "" : "s"} (${types?.state ?? "unknown"})`);
    lines.push(
      `blueprint: ${blueprint ? (blueprint.ok ? "ok" : `${blueprintErrors} error${blueprintErrors === 1 ? "" : "s"}`) : "not checked"}`,
    );
    lines.push(`build: ${build}`);
    lines.push(GENERATION_LABEL[generation] ?? `generation: ${generation}`);
  } else {
    lines.push("no status from the backend");
  }
  if (overrides?.dirty) lines.push("unsaved local edits");
  if (status?.generation?.error) lines.push(`generation error: ${status.generation.error}`);

  const level: StatusLevel =
    status == null ? "unknown" : errors > 0 ? "error" : generation !== "clean" || overrides?.dirty ? "warn" : warnings > 0 ? "warn" : "ok";

  const label =
    level === "error"
      ? `${errors} error${errors === 1 ? "" : "s"}`
      : level === "warn"
        ? generation === "running"
          ? "generating"
          : generation === "dirty"
            ? "generation dirty"
            : overrides?.dirty
              ? "unsaved changes"
              : `${warnings} warning${warnings === 1 ? "" : "s"}`
        : level === "ok"
          ? "clean"
          : // The socket's own label already says "disconnected"; the light reports what
            // it actually lacks, which is a status model to reason about.
            "no status";

  return { level, label, lines, counts: { errors, warnings } };
}
