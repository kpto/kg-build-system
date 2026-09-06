import { describe, expect, it, vi } from "vitest";

import { backoffDelay, connect, MAX_BACKOFF_MS } from "./ws";
import type { StudioEvent } from "@/lib/types";

describe("backoffDelay", () => {
  it("grows exponentially and caps at five seconds", () => {
    const at = (attempt: number) => backoffDelay(attempt, MAX_BACKOFF_MS);
    // Jitter adds up to 20 %, so bound the range rather than the exact value.
    expect(at(0)).toBeGreaterThanOrEqual(500);
    expect(at(0)).toBeLessThanOrEqual(600);
    expect(at(1)).toBeGreaterThanOrEqual(1000);
    expect(at(3)).toBeGreaterThanOrEqual(4000);
    for (const attempt of [4, 8, 20]) {
      expect(at(attempt)).toBeLessThanOrEqual(MAX_BACKOFF_MS);
    }
  });
});

/** A WebSocket double, so the client can be driven without a network. */
class FakeSocket {
  static instances: FakeSocket[] = [];
  readonly readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  readonly sent: string[] = [];
  closed = false;

  constructor(readonly url: string) {
    FakeSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.closed = true;
  }

  open(): void {
    this.onopen?.();
  }

  emit(payload: unknown): void {
    this.onmessage?.({ data: JSON.stringify(payload) });
  }
}

const attach = (events: StudioEvent[], resynced: number[] = []) => {
  FakeSocket.instances = [];
  const socket = connect({
    url: "ws://test/ws",
    createSocket: (url) => new FakeSocket(url) as unknown as WebSocket,
    fetchState: async () => ({ revision: 12, document: undefined, status: undefined }),
    onEvent: (event) => events.push(event),
    onResync: (state) => resynced.push(state.revision ?? -1),
  });
  FakeSocket.instances[0]?.open();
  return socket;
};

describe("connect", () => {
  it("subscribes and resyncs by GET /api/state on connect", async () => {
    const events: StudioEvent[] = [];
    const resynced: number[] = [];
    const socket = attach(events, resynced);
    await Promise.resolve();
    await Promise.resolve();

    expect(FakeSocket.instances[0]?.sent).toEqual([JSON.stringify({ type: "subscribe" })]);
    expect(resynced).toEqual([12]);
    expect(events.map((event) => event.type)).toContain("resync");

    socket.close();
    expect(FakeSocket.instances[0]?.closed).toBe(true);
  });

  it("forwards a modelled event and never drops an unknown one", () => {
    const events: StudioEvent[] = [];
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const socket = attach(events);

    FakeSocket.instances[0]?.emit({ type: "generation", state: "running" });
    FakeSocket.instances[0]?.emit({ type: "quarantine", detail: "new in the backend" });
    FakeSocket.instances[0]?.emit({ not: "an event" });

    expect(events.some((event) => event.type === "generation")).toBe(true);
    const unknown = events.filter((event) => event.type === "unknown");
    expect(unknown).toHaveLength(2);
    expect(unknown[0]).toMatchObject({
      name: "quarantine",
      payload: { detail: "new in the backend" },
    });
    expect(warn).toHaveBeenCalled();

    socket.close();
    warn.mockRestore();
  });

  it("reports an unparseable frame instead of throwing", () => {
    const events: StudioEvent[] = [];
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const socket = attach(events);

    FakeSocket.instances[0]?.onmessage?.({ data: "{ not json" });
    expect(events.some((event) => event.type === "unknown" && event.name === "malformed")).toBe(true);

    socket.close();
    warn.mockRestore();
  });
});
