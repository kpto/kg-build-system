import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useConnectionStore } from "./connectionStore";

/*
 * Notices float over the canvas and capture clicks where they sit, so how long one
 * lives is a correctness property, not a cosmetic one: an acknowledgement that
 * outlives its moment is an obstruction.
 */

const store = () => useConnectionStore.getState();

beforeEach(() => {
  vi.useFakeTimers();
  store().clearNotices();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("connection notices", () => {
  it("gives every notice its own id so dismissing one cannot dismiss another", () => {
    store().notice({ level: "info", text: "first" });
    store().notice({ level: "info", text: "second" });

    const [first, second] = store().notices;
    expect(first?.id).not.toBe(second?.id);

    store().dismissNotice(first!.id);
    expect(store().notices.map((item) => item.text)).toEqual(["second"]);
  });

  it("keeps the most recent six and drops the oldest", () => {
    for (let index = 0; index < 8; index += 1) {
      store().notice({ level: "info", text: `n${index}` });
    }
    expect(store().notices.map((item) => item.text)).toEqual(["n2", "n3", "n4", "n5", "n6", "n7"]);
  });

  it("retires an informational notice by itself", () => {
    store().notice({ level: "info", text: "saved" });
    expect(store().notices).toHaveLength(1);

    vi.advanceTimersByTime(6_000);
    expect(store().notices).toHaveLength(0);
  });

  it("holds an error until it is acknowledged", () => {
    store().notice({ level: "error", text: "generation failed" });

    vi.advanceTimersByTime(60_000);
    expect(store().notices.map((item) => item.text)).toEqual(["generation failed"]);

    store().dismissNotice(store().notices[0]!.id);
    expect(store().notices).toHaveLength(0);
  });

  it("gives a warning longer to be read than a routine acknowledgement", () => {
    store().notice({ level: "info", text: "saved" });
    store().notice({ level: "warn", text: "generation dirty" });

    vi.advanceTimersByTime(6_000);
    expect(store().notices.map((item) => item.text)).toEqual(["generation dirty"]);

    vi.advanceTimersByTime(6_000);
    expect(store().notices).toHaveLength(0);
  });

  it("cancels the timer of a notice dismissed by hand", () => {
    store().notice({ level: "info", text: "saved" });
    store().dismissNotice(store().notices[0]!.id);

    // Nothing is left to fire, so advancing the clock past every lifetime is inert
    // rather than a delayed second dismissal.
    store().notice({ level: "warn", text: "later" });
    vi.advanceTimersByTime(5_999);
    expect(store().notices.map((item) => item.text)).toEqual(["later"]);
  });

  it("clears every pending timer when the queue is emptied wholesale", () => {
    store().notice({ level: "info", text: "a" });
    store().notice({ level: "warn", text: "b" });
    store().clearNotices();

    vi.advanceTimersByTime(60_000);
    expect(store().notices).toHaveLength(0);
  });
});
