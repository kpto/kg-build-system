// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ProblemsPanel } from "./ProblemsPanel";
import type { Problem } from "@/lib/types";
import { useProblemStore } from "@/stores/problemStore";
import { useSelectionStore } from "@/stores/selectionStore";

afterEach(cleanup);

/** A pyright-style message: the text the user needs to be able to copy out. */
const MESSAGE = 'Argument of type "None" is not assignable to parameter of type "_Configuration"';

const problem = (id: string, over: Partial<Problem>): Problem => ({
  id,
  tier: "types",
  severity: "error",
  message: MESSAGE,
  ref: null,
  ...over,
});

const PROBLEMS: Problem[] = [
  problem("p1", { ref: "component:site", file: "studio_test_project/components.py", line: 41 }),
  problem("p2", {
    tier: "document",
    severity: "warning",
    message: "site_id has no physical column",
    ref: "table:sites.field.site_id",
    file: "project.ir.json",
    line: 88,
  }),
];

const panel = (onClose = vi.fn(), onToggle = vi.fn()) => (
  <ProblemsPanel open onToggle={onToggle} onClose={onClose} />
);

const list = () => screen.getByRole("list");
/**
 * The jump target inside each row. The copy control beside it is a genuine `<button>`;
 * the row itself must never be one, because a native button consumes the mousedown that
 * starts a text selection — which is what made the message uncopyable.
 */
const rows = () => Array.from(list().querySelectorAll<HTMLElement>('div[role="button"]'));
const copyControls = () => Array.from(list().querySelectorAll<HTMLButtonElement>("button"));
const row = (index: number) => rows()[index] as HTMLElement;

/**
 * jsdom's own selection is always collapsed, so the tests that care about one stub it:
 * `isCollapsed === false` is what a finished drag-select leaves behind.
 */
const stubSelection = (isCollapsed: boolean) =>
  vi.spyOn(window, "getSelection").mockReturnValue({ isCollapsed } as Selection);

const selection = () => useSelectionStore.getState();

beforeEach(() => {
  // The store is a module singleton, so each test starts from all tiers on.
  useProblemStore.getState().setTiers(["types", "blueprint", "build", "document"]);
  useProblemStore.getState().setProblems(PROBLEMS);
  useSelectionStore.getState().reset();
});

afterEach(() => {
  useProblemStore.getState().reset();
  useSelectionStore.getState().reset();
});

describe("ProblemsPanel rows", () => {
  it("renders each row as a focusable div, never a native button", () => {
    render(panel());

    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    for (const item of rows()) {
      // A native button consumes mousedown, which is what stopped the message being
      // selectable in the first place.
      expect(item.tagName).toBe("DIV");
      expect(item.getAttribute("role")).toBe("button");
      expect(item.tabIndex).toBe(0);
    }
    expect(list().querySelectorAll('button')).toHaveLength(2);
  });

  it("keeps the message as the row's accessible name", () => {
    render(panel());

    expect(screen.getAllByRole("button", { name: /is not assignable/ })).toHaveLength(1);
    expect(row(1).textContent).toContain("site_id has no physical column");
  });

  it("activates on Enter and on Space without letting Space scroll the panel", () => {
    render(panel());
    // Keyboard activation is unconditional: a leftover selection is not a key press.
    stubSelection(false);

    fireEvent.keyDown(row(0), { key: "Enter" });
    expect(selection().selectedRef).toBe("component:site");
    expect(selection().area).toBe("topology");

    useSelectionStore.getState().reset();
    // fireEvent returns false once preventDefault has run, i.e. the row claimed Space.
    expect(fireEvent.keyDown(row(1), { key: " " })).toBe(false);
    expect(selection().selectedRef).toBe("table:sites.field.site_id");
    expect(selection().area).toBe("contracts");
  });

  it("jumps to the clicked row's problem when no text is selected", () => {
    stubSelection(true);
    const revealed = selection().revealToken;
    render(panel());

    fireEvent.click(row(1));
    expect(selection().selectedRef).toBe("table:sites.field.site_id");
    expect(selection().area).toBe("contracts");
    expect(selection().revealToken).toBe(revealed + 1);
  });

  it("routes a problem with no ref to its area rather than doing nothing", () => {
    stubSelection(true);
    useProblemStore
      .getState()
      .setProblems([problem("p3", { tier: "build", severity: "warning", message: "build.py exited 1" })]);
    render(panel());

    fireEvent.click(row(0));
    expect(selection().selectedRef).toBeNull();
    expect(selection().area).toBe("plan");
  });

  it("leaves the view alone when the click ends a drag-select", () => {
    const revealed = selection().revealToken;
    render(panel());
    stubSelection(false);

    fireEvent.click(row(0));
    fireEvent.click(row(1));
    expect(selection().revealToken).toBe(revealed);
    expect(selection().selectedRef).toBeNull();
    expect(selection().area).toBe("topology");
  });
});

describe("ProblemsPanel structure and header", () => {
  it("exposes one list of listitems, each owning a selectable row and a copy control", () => {
    render(panel());

    // A second `role="list"` wrapping the virtualised one would be a list whose only
    // child is not a listitem, so the panel must own exactly one.
    expect(screen.getAllByRole("list")).toHaveLength(1);
    expect(list().getAttribute("aria-label")).toBe("2 problems");

    const items = within(list()).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    for (const item of items) {
      // Each row holds the selectable row itself and the copy control beside it —
      // beside, not inside, because a role="button" element owns its descendants. The
      // two sit in a layout wrapper, so the tree stays list > listitem > button.
      expect(item.querySelectorAll('div[role="button"]')).toHaveLength(1);
      expect(item.querySelectorAll("button")).toHaveLength(1);
    }
  });

  it("drops the list entirely once nothing is left to list", () => {
    useProblemStore.getState().setProblems([]);
    render(panel());

    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.getByText("No problems reported")).toBeDefined();
  });

  it("filters the list from the tier chips", () => {
    render(panel());
    expect(screen.getAllByRole("listitem")).toHaveLength(2);

    fireEvent.click(screen.getByRole("button", { name: "types 1" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
    expect(list().getAttribute("aria-label")).toBe("1 problems");
    expect(row(0).textContent).toContain("site_id has no physical column");

    fireEvent.click(screen.getByRole("button", { name: "document 1" }));
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.getByText("All problems filtered out")).toBeDefined();

    fireEvent.click(screen.getByRole("button", { name: "types 1" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(1);
  });

  it("keeps the header's collapse and close affordances working", () => {
    const onClose = vi.fn();
    const onToggle = vi.fn();
    render(panel(onClose, onToggle));

    fireEvent.click(screen.getByRole("button", { name: "Close problems panel" }));
    expect(onClose).toHaveBeenCalledTimes(1);

    const toggle = screen.getByRole("button", { name: "Problems" });
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(toggle);
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});

describe("copying a problem out", () => {
  /** jsdom ships no clipboard; each test installs the one it needs. */
  const stubClipboard = (writeText: (text: string) => Promise<void>) =>
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

  const copyButtons = () => screen.getAllByRole("button", { name: "copy" });

  it("copies the whole message, which the clipped row cannot show", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    stubClipboard(writeText);
    render(panel());

    fireEvent.click(copyButtons()[0] as HTMLElement);
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(MESSAGE));
  });

  it("copies each row's own message, not the first row's", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    stubClipboard(writeText);
    render(panel());

    fireEvent.click(copyButtons()[1] as HTMLElement);
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("site_id has no physical column"));
  });

  it("leaves the view where it was, so copying never navigates", () => {
    stubClipboard(() => Promise.resolve());
    const before = { ref: selection().selectedRef, area: selection().area, token: selection().revealToken };
    render(panel());

    fireEvent.click(copyButtons()[0] as HTMLElement);
    expect(selection().selectedRef).toBe(before.ref);
    expect(selection().area).toBe(before.area);
    expect(selection().revealToken).toBe(before.token);
  });

  it("says so when the clipboard refuses rather than claiming it copied", async () => {
    stubClipboard(() => Promise.reject(new Error("denied")));
    render(panel());

    fireEvent.click(copyButtons()[0] as HTMLElement);
    await waitFor(() => expect(screen.getAllByText("unavailable").length).toBeGreaterThan(0));
    expect(screen.queryAllByText("copied")).toHaveLength(0);
  });
});
