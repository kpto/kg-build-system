// @vitest-environment jsdom
/**
 * The canvas is a drag surface that draws its labels as SVG `<text>`, and SVG text is
 * selectable by default: dragging a node across the captions around it started a native
 * text selection that fought the drag and left the picture highlighted. The fix is
 * `select-none` on the drawing `<svg>`, which is a class, i.e. something a later edit can
 * delete without touching a line of behaviour.
 *
 * These tests therefore measure the computed style rather than the class name, and the
 * gestures that have to survive the fix: a tap selects, a plain drag places, a shift drag
 * connects, and a template stays in the library instead of floating in the graph.
 */

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import { useProblemStore } from "@/stores/problemStore";
import { buildGraph, componentRef, DEFAULT_FILTERS, templateCatalogue } from "./logic";
import { ForceGraph, type ForceGraphProps } from "./ForceGraph";
import { TemplateLibrary } from "./TemplateLibrary";

/**
 * The rule Tailwind v4 emits for `select-none`, copied verbatim from the compiled output
 * of `@import "tailwindcss"` (vendor line first, then the standard one). jsdom ships no
 * Tailwind, so without this the class name would resolve to nothing and the assertion
 * below could never pass — and, more to the point, could never fail for the right reason.
 */
const SELECT_NONE = `
.select-none { -webkit-user-select: none; user-select: none; }
`;

/** jsdom implements neither ResizeObserver nor layout; the host-measuring effect needs
 *  the constructor to exist, and the canvas then keeps its default 960×620 box. */
globalThis.ResizeObserver = class {
  observe(): void {}
  unobserve(): void {}
  disconnect(): void {}
} as unknown as typeof ResizeObserver;

const graph = buildGraph(SAMPLE_DOCUMENT, DEFAULT_FILTERS);

type Overrides = Partial<Omit<ForceGraphProps, "document" | "graph">>;

function mount(overrides: Overrides = {}) {
  const onSelectRef = vi.fn();
  const apply = vi.fn();
  const view = render(
    <>
      <style>{SELECT_NONE}</style>
      <ForceGraph
        document={SAMPLE_DOCUMENT}
        graph={graph}
        selectedRef={null}
        revealToken={0}
        revealId={null}
        onRevealConsumed={vi.fn()}
        onSelectRef={onSelectRef}
        apply={apply}
        {...overrides}
      />
    </>,
  );

  // The drawing surface is the svg the accessible title names — not the class under test,
  // so the query cannot quietly follow a rename of the thing being asserted.
  const surface = view.container.querySelector<SVGSVGElement>('svg[role="img"]');
  const host = surface?.parentElement ?? null;
  const node = (id: string) => screen.queryByTestId(`graph-node-${id}`);
  return { view, surface, host, node, onSelectRef, apply };
}

/** Every `<text>` the canvas draws a vertex with: the captions a drag passes over. */
const captionsIn = (surface: Element) =>
  Array.from(surface.querySelectorAll("text")).filter((text) => text.textContent?.trim());

/** Walk from `leaf` up to `surface`, so an opt-out anywhere between them is visible. */
const chainToSurface = (surface: Element, leaf: Element): Element[] => {
  const chain: Element[] = [];
  for (let el: Element | null = leaf; el && el !== surface; el = el.parentElement) chain.push(el);
  return chain;
};

/** Tailwind's other `select-*` utilities: a deliberate opt back into selection. */
const SELECTABLE = /\bselect-(text|all|auto|contain)\b/;

beforeEach(() => {
  useProblemStore.getState().reset();
});

afterEach(cleanup);

describe("the drawing surface and the text on it", () => {
  it("computes user-select:none, so a node drag cannot start a text selection", () => {
    const { surface } = mount();
    expect(surface).not.toBeNull();
    const svg = surface as SVGSVGElement;

    // The computed value, not the class name: drop `select-none` from the svg and the
    // injected rule matches nothing, so this reads the property's initial value instead of
    // `none` (jsdom reports it as `""`) and the test goes red. Checked by hand, both ways.
    expect(getComputedStyle(svg).userSelect).toBe("none");

    // …and the value comes from that rule, not from a jsdom default: the host div around
    // the svg, which carries no such class, still computes something else.
    const host = svg.parentElement;
    expect(host && getComputedStyle(host).userSelect).not.toBe("none");
  });

  it("draws the captions inside that surface, and nothing opts them back in", () => {
    const { surface } = mount();
    const svg = surface as SVGSVGElement;
    const captions = captionsIn(svg);

    // Not an empty wrapper: the labels the user complained about really are descendants.
    expect(captions.length).toBeGreaterThan(0);
    const site = captions.find((text) => text.textContent === "site");
    expect(site?.tagName.toLowerCase()).toBe("text"); // SVG text: selectable by default
    expect(svg.contains(site as Element)).toBe(true);

    // The surface's value is the last word on them — no ancestor between the caption and
    // the svg re-enables selection the way the plan card's ref line does on purpose.
    const chain = chainToSurface(svg, site as Element);
    expect(chain.length).toBeGreaterThan(0);
    for (const el of chain) {
      expect(el.className?.toString() ?? "").not.toMatch(SELECTABLE);
      expect(el.getAttribute("style") ?? "").not.toMatch(/user-select/i);
    }
  });
});

describe("the gestures on a vertex", () => {
  it("treats a press with no movement as a selection, not a drag", () => {
    const { node, surface, onSelectRef, apply } = mount();
    const site = node("site");
    expect(site).not.toBeNull();

    fireEvent.pointerDown(site as Element, { pointerId: 1, clientX: 40, clientY: 40 });
    fireEvent.pointerUp(site as Element, { pointerId: 1, clientX: 40, clientY: 40 });

    // A tap writes nothing, and it selects: exactly one call, carrying the vertex's ref.
    expect(onSelectRef.mock.calls).toEqual([[componentRef("site")]]);
    expect(apply).not.toHaveBeenCalled();

    // The press landed on the vertex rather than the pane behind it — the pane answers the
    // same gesture by clearing the selection, which is the opposite of what was reported.
    onSelectRef.mockClear();
    const pane = surface?.querySelector('[data-graph-pane="true"]');
    expect(pane).not.toBeNull();
    fireEvent.pointerDown(pane as Element, { pointerId: 5, clientX: 5, clientY: 5 });
    expect(onSelectRef).toHaveBeenCalledWith(null);
  });

  it("moves and persists on a plain drag, so the fix did not eat the drag", () => {
    const { node, host, onSelectRef, apply } = mount();
    const site = node("site") as Element;
    const placedBefore = site.getAttribute("transform");
    expect(placedBefore).toMatch(/^translate\(/);

    fireEvent.pointerDown(site, { pointerId: 2, clientX: 40, clientY: 40 });
    fireEvent.pointerMove(host as Element, { pointerId: 2, clientX: 360, clientY: 300 });

    // Only that the node left its seat, never where it landed: the layout is a view and
    // its coordinates are not this test's to pin down.
    expect(site.getAttribute("transform")).not.toBe(placedBefore);

    fireEvent.pointerUp(host as Element, { pointerId: 2, clientX: 360, clientY: 300 });
    expect(apply).toHaveBeenCalledTimes(1);
    expect(onSelectRef).not.toHaveBeenCalled();
  });

  it("connects instead of moving when shift is held", () => {
    const { node, host, surface, apply } = mount();
    const site = node("site") as Element;
    const placedBefore = site.getAttribute("transform");

    fireEvent.pointerDown(site, { pointerId: 3, clientX: 40, clientY: 40, shiftKey: true });
    fireEvent.pointerMove(host as Element, { pointerId: 3, clientX: 360, clientY: 300 });

    // The rubber band is the DOM signature of the connect gesture…
    expect(surface?.querySelector('line[stroke-dasharray="5 4"]')).not.toBeNull();
    // …and the two gestures stay distinguishable: the same movement without shift moved
    // the node, this one leaves it exactly where the layout put it and writes nothing.
    expect(site.getAttribute("transform")).toBe(placedBefore);
    expect(apply).not.toHaveBeenCalled();
  });

  it("exposes every drawn vertex as a draggable, tier-tagged group", () => {
    const { node } = mount();

    for (const vertex of graph.vertices) {
      const group = node(vertex.id);
      expect(group, `graph-node-${vertex.id}`).not.toBeNull();
      expect(group?.getAttribute("data-shape")).toBe(vertex.shape);
      expect(group?.getAttribute("data-tier")).toBe(vertex.component.tier);
      // No transform means no pointer target: the vertex was never placed on the canvas.
      expect(group?.getAttribute("transform")).toMatch(/^translate\(/);
    }
  });
});

describe("mix-in templates", () => {
  it("live in the library and never become a vertex on the canvas", () => {
    const entries = templateCatalogue(SAMPLE_DOCUMENT);
    expect(entries.map((entry) => entry.component.id)).toContain("provenanced_node");

    const { node } = mount();
    render(<TemplateLibrary entries={entries} selectedRef={null} onSelectRef={vi.fn()} />);

    expect(screen.getAllByText("provenanced_node")).toHaveLength(1); // the library row
    expect(node("provenanced_node")).toBeNull();
    // The components that mix it in are drawn, so this is exclusion, not a blank canvas.
    expect(node("site")).not.toBeNull();
  });
});
