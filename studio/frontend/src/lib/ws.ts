/**
 * Reconnecting WebSocket for `/ws`.
 *
 * Rules from API.md: the client must resync by revision after any reconnect (a
 * dropped socket must never leave the UI editing a stale revision), and it must
 * never drop an event type it does not know — an unknown `type` is logged and
 * forwarded as `{type: "unknown"}` so a backend addition shows up rather than
 * disappearing silently.
 */

import { api, WS_URL } from "./api";
import type { JsonObject, ProjectDocument } from "./ir";
import type { StatusModel, StudioEvent } from "./types";

export const MAX_BACKOFF_MS = 5_000;
const BASE_BACKOFF_MS = 500;

export interface StudioSocket {
  readonly url: string;
  /** Handshake state, for the connection store. */
  readonly state: () => WebSocketState;
  close(): void;
}

export type WebSocketState = "connecting" | "open" | "closed" | "error";

export interface ConnectOptions {
  url?: string;
  onEvent(event: StudioEvent): void;
  /**
   * Called on every (re)connect with the result of `GET /api/state`. The caller
   * adopts document + revision, which is what makes the resync authoritative.
   */
  onResync?(state: { document?: ProjectDocument; revision?: number; status?: StatusModel }): void;
  /** Injectable for tests; defaults to `api.getState`. */
  fetchState?(): Promise<{ document?: ProjectDocument; revision?: number; status?: StatusModel }>;
  /** Injectable for tests. */
  createSocket?(url: string): WebSocket;
  maxBackoffMs?: number;
}

const KNOWN_TYPES = new Set([
  "hello",
  "document",
  "generation",
  "diagnostics",
  "blueprint",
  "plan",
  "build",
  "log",
]);

function asJsonObject(value: unknown): JsonObject {
  return value && typeof value === "object" ? (value as JsonObject) : {};
}

/**
 * Exponential backoff with jitter, capped at `maxBackoffMs` (5 s by default).
 * `attempt` resets to 0 as soon as the socket opens.
 */
export function backoffDelay(attempt: number, max: number = MAX_BACKOFF_MS): number {
  const growth = BASE_BACKOFF_MS * 2 ** Math.max(0, attempt);
  const capped = Math.min(max, growth);
  const jitter = capped * 0.2 * Math.random();
  return Math.round(Math.min(max, capped + jitter));
}

/**
 * Open the studio event stream. Returns a handle whose `close()` is permanent:
 * the reconnect loop stops and the socket is released.
 */
export function connect(options: ConnectOptions): StudioSocket {
  const url = options.url ?? WS_URL;
  const fetchState = options.fetchState ?? (() => api.getState());
  const maxBackoff = options.maxBackoffMs ?? MAX_BACKOFF_MS;
  const openSocket = options.createSocket ?? ((target: string) => new WebSocket(target));

  let closed = false;
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let attempt = 0;
  let current: WebSocketState = "connecting";

  const setState = (state: WebSocketState, detail?: string) => {
    current = state;
    options.onEvent({ type: "socket", state, ...(detail ? { detail } : {}) });
  };

  const resync = async () => {
    try {
      const state = await fetchState();
      if (closed) return;
      options.onResync?.(state);
      options.onEvent({ type: "resync", ...state });
    } catch (error) {
      // A failed resync must not kill the socket: the next event still applies.
      options.onEvent({
        type: "log",
        level: "warn",
        text: `resync failed: ${error instanceof Error ? error.message : String(error)}`,
      });
    }
  };

  const scheduleReconnect = () => {
    if (closed || timer) return;
    const delay = backoffDelay(attempt, maxBackoff);
    attempt += 1;
    timer = setTimeout(() => {
      timer = null;
      open();
    }, delay);
  };

  const handle = (raw: unknown) => {
    if (!raw || typeof raw !== "object") {
      console.warn("[ws] non-object frame ignored", raw);
      options.onEvent({ type: "unknown", name: "invalid", payload: asJsonObject(raw) });
      return;
    }
    const payload = raw as Record<string, unknown>;
    const type = typeof payload["type"] === "string" ? payload["type"] : "";
    if (!KNOWN_TYPES.has(type)) {
      // Never drop it: log and forward so the shell can still show or ignore it.
      console.warn(`[ws] unknown event type ${JSON.stringify(type)}`, payload);
      options.onEvent({ type: "unknown", name: type || "(missing)", payload: asJsonObject(payload) });
      return;
    }
    options.onEvent(payload as unknown as StudioEvent);
  };

  const open = () => {
    if (closed) return;
    setState("connecting");
    let created: WebSocket;
    try {
      created = openSocket(url);
    } catch (error) {
      setState("error", error instanceof Error ? error.message : String(error));
      scheduleReconnect();
      return;
    }
    socket = created;

    created.onopen = () => {
      if (closed) return;
      attempt = 0;
      setState("open");
      try {
        created.send(JSON.stringify({ type: "subscribe" }));
      } catch {
        // A socket that opened then refused the subscribe frame still resyncs by REST.
      }
      void resync();
    };

    created.onmessage = (event: MessageEvent) => {
      const raw = event.data;
      if (typeof raw !== "string") {
        console.warn("[ws] non-text frame ignored");
        return;
      }
      let parsed: unknown;
      try {
        parsed = JSON.parse(raw);
      } catch (error) {
        console.warn("[ws] unparseable frame ignored", error, raw.slice(0, 120));
        options.onEvent({ type: "unknown", name: "malformed", payload: {} });
        return;
      }
      handle(parsed);
    };

    created.onerror = (event: Event) => {
      const target = event.target as WebSocket | null;
      setState("error", target?.url ? `socket error on ${target.url}` : "socket error");
    };

    created.onclose = () => {
      socket = null;
      if (closed) {
        setState("closed");
        return;
      }
      setState("closed");
      scheduleReconnect();
    };
  };

  open();

  return {
    url,
    state: () => current,
    close() {
      closed = true;
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      const active = socket;
      socket = null;
      if (active) {
        active.onclose = null;
        active.onmessage = null;
        active.onerror = null;
        active.onopen = null;
        try {
          active.close();
        } catch {
          // already closing
        }
      }
      current = "closed";
    },
  };
}
