// @vitest-environment jsdom
import { cleanup, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { NodeProps } from "@xyflow/react";

import { StepNodeCard, type StepFlowNode } from "./StepNode";
import { stepDetail } from "./detail";
import type { StepDetail, StepNode } from "./types";

/**
 * The ref line is the plan canvas's only way out to the declaration a step came from,
 * and it used to be a native `<button>`: the button consumed the mousedown, so the ref
 * could not be drag-selected and could not be copied. The three rules that keep it both
 * clickable and copyable are measured here.
 */

const REF = "table:equipment";

const step: StepNode = {
  id: "core::table.equipment",
  module_id: "core",
  label: "equipment",
  kind: "table",
  component: REF,
  // No sockets: the card then renders without a React Flow handle, so it needs no
  // node context to be mounted on its own.
  inputs: [],
  outputs: [],
};

const detail: StepDetail = { ...stepDetail(step, [], null) };

/**
 * The two stylesheet rules the browser actually resolves, taken verbatim from
 * `@xyflow/react/dist/style.css` and from the Tailwind v4 output for `select-text`.
 * jsdom ships neither, so the test brings the cascade the card lives inside: React
 * Flow's `user-select: none` on `.react-flow__node` is what makes swapping the element
 * alone insufficient.
 */
const CASCADE = `
.react-flow__node { user-select: none; -webkit-user-select: none; }
.select-text { user-select: text; -webkit-user-select: text; }
`;

const mount = (onSelect = vi.fn(), selected = false) => {
  const props = {
    id: step.id,
    type: "step",
    data: {
      step,
      detail,
      laneColor: "#888888",
      selected,
      dimmed: false,
      problems: [],
      onSelect,
      onOpenSql: vi.fn(),
      onHover: vi.fn(),
    },
  } as unknown as NodeProps<StepFlowNode>;

  const view = render(
    <>
      <style>{CASCADE}</style>
      <div className="react-flow__node">
        <StepNodeCard {...props} />
      </div>
    </>,
  );
  const refRow = view.getByRole("button", { name: REF });
  const copy = view.getByRole("button", { name: "copy" });
  return { view, onSelect, refRow: refRow as HTMLElement, copy: copy as HTMLElement };
};

/** jsdom's selection is always collapsed; a finished drag-select leaves this behind. */
const stubSelection = (isCollapsed: boolean) =>
  vi.spyOn(window, "getSelection").mockReturnValue({ isCollapsed } as Selection);

const clipboard = (writeText: (text: string) => Promise<void>) =>
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

afterEach(cleanup);

describe("the ref line of a plan card", () => {
  it("is a role=button div, never a native button", () => {
    const { refRow } = mount();

    expect(refRow.tagName).toBe("DIV");
    expect(refRow.getAttribute("role")).toBe("button");
    // A native button — as this element or as an ancestor — consumes the mousedown
    // that starts a text selection.
    expect(refRow.closest("button")).toBeNull();
    expect(refRow.tabIndex).toBe(0);
    expect(refRow.textContent).toBe(REF);
  });

  it("computes user-select:text while the React Flow node around it computes none", () => {
    const { refRow } = mount();
    const node = refRow.closest<HTMLElement>(".react-flow__node");

    // The override has to be on the text itself: `none` on the node would otherwise
    // be inherited by every child and the ref would stay unselectable.
    expect(node && getComputedStyle(node).userSelect).toBe("none");
    expect(getComputedStyle(refRow).userSelect).toBe("text");
  });

  it("yields the drag to the text and only the text, so the card still moves", () => {
    const { refRow } = mount();
    // React Flow's documented conventions: a gesture starting on the ref selects text
    // rather than panning the canvas or dragging the card.
    const guarded = refRow.closest(".nopan");
    expect(guarded).not.toBeNull();
    expect(guarded?.classList.contains("nodrag")).toBe(true);
    // Nothing outside that wrapper is excused, so a drag anywhere else on the card
    // still reaches React Flow and moves the view.
    const card = refRow.closest<HTMLElement>("[data-step-id]");
    expect(card?.className).not.toMatch(/\bnopan\b|\bnodrag\b/);
    expect(card?.querySelectorAll(".nopan, .nodrag")).toHaveLength(1);
    expect(card?.querySelectorAll(".nopan, .nodrag")[0]).toBe(guarded);
  });

  it("selects the step when the press was a click", () => {
    stubSelection(true);
    const { onSelect, refRow } = mount();

    fireEvent.click(refRow);
    expect(onSelect).toHaveBeenCalledWith(REF);
  });

  it("does nothing when the click only ended a drag-select", () => {
    stubSelection(false);
    const { onSelect, refRow } = mount();

    fireEvent.mouseDown(refRow);
    fireEvent.click(refRow);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("activates on Enter and on Space even with a selection on screen", () => {
    // A leftover selection says nothing about an explicit key press.
    stubSelection(false);
    const { onSelect, refRow } = mount();

    fireEvent.keyDown(refRow, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith(REF);

    onSelect.mockClear();
    // fireEvent returns false once preventDefault has run: the row claimed Space.
    expect(fireEvent.keyDown(refRow, { key: " " })).toBe(false);
    expect(onSelect).toHaveBeenCalledWith(REF);
  });

  it("toggles the selection off when the already-selected ref is clicked", () => {
    stubSelection(true);
    const { onSelect, refRow } = mount(vi.fn(), true);

    expect(refRow.getAttribute("aria-current")).toBe("true");
    fireEvent.click(refRow);
    expect(onSelect).toHaveBeenCalledWith(null);
  });

  it("hands the whole ref to the clipboard, because the row clips it", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    clipboard(writeText);
    const { copy, refRow, onSelect } = mount();

    // The row truncates: a drag reaches only the visible part, so the complete string
    // has to be one click away.
    expect(refRow.className).toMatch(/\btruncate\b/);
    // Beside the row rather than inside it — `role="button"` owns its descendants.
    expect(refRow.contains(copy)).toBe(false);

    fireEvent.click(copy);
    await vi.waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(REF);
      expect(copy.textContent).toBe("copied");
    });
    // Copying is not a way of changing what is selected.
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("says so when the clipboard refuses", async () => {
    clipboard(() => Promise.reject(new Error("denied")));
    const { copy } = mount();

    fireEvent.click(copy);
    await vi.waitFor(() => expect(copy.textContent).toBe("unavailable"));
  });
});
