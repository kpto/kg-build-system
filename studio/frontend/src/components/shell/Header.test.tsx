// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import type { Notice } from "@/lib/types";
import { statusLight } from "@/stores/connectionStore";
import { Header } from "./Header";

afterEach(cleanup);

const notice = (id: string, level: Notice["level"] = "info"): Notice => ({ id, level, text: id, at: 0 });

const header = (notices: Notice[], onDismissNotice = vi.fn(), onClearNotices = vi.fn()) => (
  <Header
    document={SAMPLE_DOCUMENT}
    revision={12}
    dirty={false}
    sending={false}
    mock
    light={statusLight(null)}
    socket="off"
    notices={notices}
    canUndo={false}
    canRedo={false}
    onUndo={vi.fn()}
    onRedo={vi.fn()}
    onDismissNotice={onDismissNotice}
    onClearNotices={onClearNotices}
    inspectorOpen={false}
    onToggleInspector={vi.fn()}
    problemsOpen={false}
    onToggleProblems={vi.fn()}
    problemCount={0}
    searchValue=""
    onSearchChange={vi.fn()}
    onSearchFocus={vi.fn()}
    paletteOpen={false}
  />
);

const dismissButtons = () => screen.getAllByRole("button", { name: "dismiss" });

/** A card is whatever wraps one notice's dismiss button. */
const cards = () => dismissButtons().map((dismiss) => dismiss.parentElement as Element);

describe("Header notices", () => {
  it("keeps the stack click-through but hands each card its own pointer events back", () => {
    render(header([notice("n1"), notice("n2", "warn")]));

    expect(cards()).toHaveLength(2);
    // Without `pointer-events-auto` the wrapper swallows the click and no notice can
    // ever be dismissed, which is the bug this guards.
    for (const card of cards()) {
      expect(card.classList.contains("pointer-events-auto")).toBe(true);
    }
    expect(screen.getByRole("status").classList.contains("pointer-events-none")).toBe(true);
  });

  it("dismisses exactly the notice whose button was pressed", () => {
    const onDismissNotice = vi.fn();
    render(header([notice("n1"), notice("n2", "error")], onDismissNotice));

    fireEvent.click(dismissButtons()[1] as HTMLElement);
    expect(onDismissNotice).toHaveBeenCalledTimes(1);
    expect(onDismissNotice).toHaveBeenCalledWith("n2");
  });

  it("renders one card per notice and none at all once the queue empties", () => {
    const { rerender } = render(header([notice("n1"), notice("n2"), notice("n3")]));
    expect(dismissButtons()).toHaveLength(3);

    rerender(header([]));
    expect(screen.queryByRole("status")).toBeNull();
  });

  it("offers to clear the whole stack only once there is a stack to clear", () => {
    const { rerender } = render(header([notice("n1")]));
    expect(screen.queryByRole("button", { name: /^clear / })).toBeNull();

    const onClearNotices = vi.fn();
    rerender(header([notice("n1"), notice("n2")], vi.fn(), onClearNotices));
    fireEvent.click(screen.getByRole("button", { name: "clear 2" }));
    expect(onClearNotices).toHaveBeenCalledTimes(1);
  });
});
