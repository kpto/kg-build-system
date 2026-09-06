// @vitest-environment jsdom
/**
 * Starting a stack that holds nothing yet.
 *
 * An empty stack is the one state where the palette answers for the head rather than for
 * the next block, so these assert both halves: the rules the head is judged by
 * (`rules.checkHead`, `logic.headsFor`) and what the author can actually reach by
 * clicking. The fixtures are the mock project, whose every column is nullable and whose
 * `SiteNode.city` slot is not — the ordinary case, and the one that used to be a dead end.
 */

import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi, type Mock } from "vitest";

import { MOCK_INDEX } from "@/lib/mock";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import { array, nullable, structRef, unit, type Binding, type Expression, type LogicalType, type ProjectDocument } from "@/lib/ir";
import type { ResolvedProperty } from "@/lib/types";
import { buildBindingContext } from "../logic/context";
import { expressionAt, findBinding, type StackTarget } from "../logic/edits";
import { headsFor } from "../logic/palette";
import { checkHead, slotFor, type HeadTarget } from "../logic/rules";
import { StackComposer, type StackComposerProps } from "./StackComposer";

const ctx = buildBindingContext(SAMPLE_DOCUMENT as unknown as ProjectDocument, MOCK_INDEX);
const SITES = "kg_project.table.sites";
const maybeStr: LogicalType = nullable(unit("str"));

const CITY: StackTarget = { part: "property", name: "city" };

/** A binding that owes its `city` slot: the state every new binding property starts in. */
const unfilled: Binding = {
  id: "site_binding",
  kind: "node",
  component: "site",
  build_key: { kind: "field", source: "sites", path: ["site_id"], logical_type: unit("str") },
  properties: [],
};

function renderComposer(overrides: Partial<StackComposerProps> = {}): Mock {
  const apply = vi.fn();
  render(
    <StackComposer
      ctx={ctx}
      binding={unfilled}
      target={CITY}
      slot={slotFor(ctx, "site", "city")}
      componentName="SiteNode"
      operators={MOCK_INDEX.operators ?? []}
      problems={[]}
      apply={apply}
      {...overrides}
    />,
  );
  return apply;
}

/** The document the composer handed `apply`, run over the fixture document. */
function writtenBy(apply: Mock, target: StackTarget = CITY): Expression | null {
  expect(apply).toHaveBeenCalledTimes(1);
  const mutate = apply.mock.calls[0]?.[0] as (draft: ProjectDocument) => ProjectDocument;
  const binding = findBinding(mutate(SAMPLE_DOCUMENT as unknown as ProjectDocument), "site_binding");
  return binding ? expressionAt(binding, target) : null;
}

const openPalette = () => {
  fireEvent.click(screen.getByRole("button", { name: "start the stack" }));
  return screen.getByRole("dialog", { name: "Add a block" });
};

/* ------------------------------------------------------------------- the empty composer */

describe("an empty stack", () => {
  afterEach(cleanup);

  it("reaches the palette from the message that asks for a source", () => {
    renderComposer();
    expect(screen.getByText(/this slot is unfilled/)).toBeDefined();
    const start = screen.getByRole("button", { name: "start the stack" });
    expect(start.hasAttribute("disabled")).toBe(false);
    fireEvent.click(start);
    const menu = screen.getByRole("dialog", { name: "Add a block" });
    // The columns are offered under the source they read, and every operation stays
    // listed but refused — with no tip there is nothing to filter it against.
    expect(within(menu).getByRole("button", { name: /^site_name/ })).toBeDefined();
    expect(within(menu).getAllByText(/a stack starts by picking a table or projection/).length).toBeGreaterThan(0);
    expect(within(menu).queryByRole("button", { name: /Keep rows where present/ })).toBeNull();
  });

  it("starts the stack with the field picked from the palette, as one edit", () => {
    const apply = renderComposer();
    fireEvent.click(within(openPalette()).getByRole("button", { name: /premises\.contact\.location\.city/ }));
    expect(writtenBy(apply)).toEqual({
      kind: "field",
      source: "sites",
      path: ["premises", "contact", "location", "city"],
      logical_type: maybeStr,
    });
  });

  it("names the unwrap a nullable head still needs rather than hiding the column", () => {
    renderComposer();
    // Every column of this project is nullable and the slot is not, so the note is on
    // all of them: the head is legal, and `where_present` is the block that finishes it.
    expect(within(openPalette()).getAllByText(/str \| None · needs keep rows where present/).length).toBeGreaterThan(0);
  });

  it("refuses a head that can never fill the slot, in the slot's own words", () => {
    renderComposer();
    const menu = openPalette();
    expect(within(menu).queryByRole("button", { name: /priority_scores/ })).toBeNull();
    expect(within(menu).getAllByText(/SiteNode\.city expects UnitType\(name='str'\), but the expression resolves to ArrayType/).length).toBeGreaterThan(0);
  });

  it("starts the stack with a written value of the slot's type", () => {
    const apply = renderComposer();
    const menu = openPalette();
    fireEvent.change(within(menu).getByRole("textbox"), { target: { value: "Rotterdam" } });
    fireEvent.click(within(menu).getByRole("button", { name: "write this value" }));
    expect(writtenBy(apply)).toEqual({ kind: "literal", value: "Rotterdam", logical_type: unit("str") });
  });

  it("will not start a stack on a value that has not been written", () => {
    renderComposer();
    const menu = openPalette();
    expect(within(menu).getByRole("button", { name: "write this value" }).hasAttribute("disabled")).toBe(true);
  });

  it("starts an empty key from a scalar column, a nullable one included", () => {
    const apply = renderComposer({
      binding: { ...unfilled, build_key: null as unknown as Expression },
      target: { part: "build_key" },
      slot: null,
    });
    expect(screen.getByText(/this key has no expression yet/)).toBeDefined();
    fireEvent.click(within(openPalette()).getByRole("button", { name: /^in_service/ }));
    expect(writtenBy(apply, { part: "build_key" })).toEqual({
      kind: "field",
      source: "equipment",
      path: ["in_service"],
      logical_type: nullable(unit("bool")),
    });
  });

  it("edits a stack that has already started exactly as it did", () => {
    const started: Binding = {
      ...unfilled,
      properties: [{ name: "city", expression: { kind: "field", source: "sites", path: ["site_name"], logical_type: maybeStr } }],
    };
    renderComposer({ binding: started });
    expect(screen.queryByText(/this slot is unfilled/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /add a block/ }));
    const menu = screen.getByRole("dialog", { name: "Add a block" });
    // The heads are gone again: this stack has a head, and the tip filters the operations.
    expect(within(menu).queryByText("site_name")).toBeNull();
    expect(within(menu).getByRole("button", { name: /Keep rows where present/ })).toBeDefined();
  });
});

/* ---------------------------------------------------------------------------- the rule */

const citySlot: ResolvedProperty = { name: "city", logical_type: unit("str"), optional: false, declared_by: "site" };
const slotTarget: HeadTarget = { componentName: "SiteNode", slot: citySlot, key: null };

describe("head legality", () => {
  it("offers a nullable column for a non-null slot because the stack unwraps it", () => {
    expect(checkHead(maybeStr, slotTarget)).toEqual({ ok: true, unwrap: true, message: null });
  });

  it("accepts a head that already satisfies the slot without asking for an unwrap", () => {
    expect(checkHead(unit("str"), slotTarget)).toEqual({ ok: true, unwrap: false, message: null });
    expect(checkHead(unit("str"), { ...slotTarget, slot: { ...citySlot, logical_type: maybeStr } })).toEqual({
      ok: true,
      unwrap: false,
      message: null,
    });
  });

  it("refuses a head of the wrong kind with the sentence the finished stack is refused in", () => {
    const check = checkHead(array(unit("str")), slotTarget);
    expect(check.ok).toBe(false);
    expect(check.message).toBe(
      "SiteNode.city expects UnitType(name='str'), but the expression resolves to ArrayType(item=UnitType(name='str'))",
    );
  });

  it("does not offer an unwrap that would not reach the slot's type", () => {
    // `where_present` takes the null off the list itself, never off its items.
    const listOfText: HeadTarget = { ...slotTarget, slot: { ...citySlot, logical_type: array(unit("str")) } };
    expect(checkHead(array(maybeStr), listOfText)).toMatchObject({ ok: false, unwrap: false });
    expect(checkHead(nullable(array(unit("str"))), listOfText)).toMatchObject({ ok: true, unwrap: true });
  });

  it("judges a key head by the key rules, scalar before nullable", () => {
    const keyTarget: HeadTarget = { componentName: "SiteNode", slot: null, key: "build_key" };
    expect(checkHead(maybeStr, keyTarget)).toEqual({ ok: true, unwrap: true, message: null });
    expect(checkHead(unit("str"), keyTarget).ok).toBe(true);
    expect(checkHead(structRef(SITES, "PremisesStruct"), keyTarget).message).toMatch(/must be a scalar/);
  });

  it("says nothing against a head when the component declares no such slot", () => {
    expect(checkHead(maybeStr, { ...slotTarget, slot: null }).ok).toBe(true);
  });
});

/* --------------------------------------------------------------------- the head palette */

describe("the heads the palette offers", () => {
  const heads = () => headsFor(ctx, slotTarget);

  it("lists every flattened path of every source, grouped by the source it reads", () => {
    const groups = heads()
      .filter((entry) => entry.operator === "field")
      .map((entry) => entry.group);
    expect([...new Set(groups)]).toEqual(["sites", "equipment", "readings.temperature", "site_cities"]);
    expect(groups).toHaveLength((MOCK_INDEX.selectable ?? []).reduce((total, entry) => total + (entry.paths?.length ?? 0), 0));
  });

  it("offers a written value typed as the slot it fills", () => {
    const written = heads().find((entry) => entry.operator === "literal");
    expect(written).toMatchObject({ enabled: true, label: "Write a value", head: { kind: "literal", type: unit("str") } });
  });

  it("withholds a written value from a slot that cannot hold one", () => {
    const record: HeadTarget = {
      componentName: "SiteNode",
      slot: { ...citySlot, logical_type: structRef(SITES, "PremisesStruct") },
      key: null,
    };
    expect(headsFor(ctx, record).some((entry) => entry.operator === "literal")).toBe(false);
  });

  it("writes the head a picked field stands for, so the stack starts folded", () => {
    const field = heads().find((entry) => entry.label === "premises.contact.email");
    expect(field?.head).toEqual({ kind: "source", source: "sites", path: ["premises", "contact", "email"] });
  });
});
