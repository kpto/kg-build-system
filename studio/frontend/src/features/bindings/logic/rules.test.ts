/**
 * The pure rules of the stack composer.
 *
 * These are the framework's rules restated in TypeScript (`ir/infer.py`,
 * `binding/factories.py`, `generate/expressions.py`), so the tests assert the
 * behaviour `docs/AUTHORING_IR_CONTRACT.md` states rather than the shape of a
 * component. The fixtures are the mock project, which is the sample document's exact
 * serialization, so a test that reads `sites.premises.contact.location.city` is
 * reading the same flattened path the backend publishes.
 */

import { describe, expect, it } from "vitest";

import type { BindingContext } from "./context";
import { compatible, resolvedSlots, structMembers } from "./context";
import { fieldPathType } from "./typecheck";
import { blockFor, matchesShape, paletteFor, spell } from "./palette";
import {
  literalExpressionText,
  memberNameOf,
  renderField,
  renderPreview,
  typeObjectText,
} from "./preview";
import {
  bindingIdFor,
  checkKey,
  checkSlot,
  concreteDescendants,
  domainRepr,
  endpointSides,
  unboundSlots,
} from "./rules";
import {
  blocksFromExpression,
  expressionFromBlocks,
  moveBlocks,
  removeBlock,
  reseatHead,
  seamsFor,
  tipType,
  type Block,
  type OperationBlock,
} from "./stack";
import { array, nullable, structRef, unit, type Expression, type LogicalType, type ProjectDocument, type StructType } from "@/lib/ir";
import { MOCK_INDEX } from "@/lib/mock";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import type { OperatorEntry, ResolvedProperty } from "@/lib/types";
import type { Binding } from "@/lib/ir";

const ctx: BindingContext = { document: SAMPLE_DOCUMENT as unknown as ProjectDocument, index: MOCK_INDEX };

const SITES = "kg_project.table.sites";
const maybeStr: LogicalType = nullable(unit("str"));

/** The catalogue filtered exactly as `index.operators` arrives from `/api/index`. */
const operators = MOCK_INDEX.operators ?? [];
const entryFor = (operator: string, side?: "prepend" | "append") => {
  const entry = operators.find((item) => item.operator === operator);
  if (!entry) throw new Error(`the index does not list ${operator}`);
  const [paletteEntry] = paletteFor(ctx, [entry], tipFor(operator)).filter((item) => !item.side || item.side === side);
  if (!paletteEntry) throw new Error(`no palette entry for ${operator}`);
  return paletteEntry;
};
const tipFor = (operator: string): LogicalType =>
  ({
    where_present: maybeStr,
    coalesce: maybeStr,
    keep_if: unit("str"),
    expand: array(structRef(SITES, "PremisesStruct")),
    struct_field: nullable(structRef(SITES, "PremisesStruct")),
    map_items: array(nullable(structRef(SITES, "PremisesStruct"))),
    without_nulls: array(maybeStr),
    sorted: array(unit("str")),
    distinct: array(unit("str")),
    join: array(unit("str")),
    add: unit("int"),
    subtract: unit("float"),
    text: unit("int"),
    concat: unit("str"),
    split_after: unit("str"),
    split_before: unit("str"),
    replaced: unit("str"),
    equals: unit("str"),
    not: unit("bool"),
    and: unit("bool"),
    or: unit("bool"),
  })[operator] ?? unit("str");

const source = (path: readonly string[], from = "sites"): Block => ({
  id: "head",
  role: "head",
  kind: "source",
  source: from,
  path,
});

const step = (operator: string, extra: Partial<OperationBlock> = {}): OperationBlock => ({
  id: `step-${operator}`,
  role: "step",
  kind: "operation",
  operator,
  parameters: {},
  operands: [],
  ...extra,
});

/* --------------------------------------------------------------------- availability */

describe("operator availability", () => {
  it("refuses every calculation on a nullable tip and names the unwrap that fixes it", () => {
    for (const operator of ["concat", "equals", "split_after", "replaced", "add"]) {
      const entry = operators.find((item) => item.operator === operator) as OperatorEntry;
      const [blocked] = paletteFor(ctx, [entry], maybeStr);
      expect(blocked?.enabled, `${operator} on ${spell(maybeStr)}`).toBe(false);
      expect(blocked?.reason).toMatch(/non-null|never missing/);
    }
  });

  it("offers the two unwraps and only the unwraps under a nullable tip", () => {
    const palette = paletteFor(ctx, operators, maybeStr);
    const enabled = palette.filter((item) => item.enabled).map((item) => item.operator);
    expect(enabled.sort()).toEqual(["coalesce", "keep_if", "where_present"]);
    const fix = palette.find((item) => item.operator === "concat");
    expect(fix?.fix?.label).toMatch(/Keep rows where present/);
  });

  it("accepts a calculation once the tip is non-null", () => {
    const palette = paletteFor(ctx, operators, unit("str"));
    const enabled = palette.filter((item) => item.enabled).map((item) => item.operator);
    expect(enabled).toEqual(expect.arrayContaining(["concat", "equals", "split_after", "replaced", "keep_if"]));
    expect(enabled).not.toContain("where_present");
    expect(enabled).not.toContain("add");
  });

  it("gives add to a number once the null is gone, and not before", () => {
    const nullableInt: LogicalType = nullable(unit("int"));
    const blocked = paletteFor(ctx, operators, nullableInt).find((item) => item.operator === "add");
    expect(blocked?.enabled).toBe(false);
    expect(blocked?.reason).toMatch(/never missing/);
    expect(blocked?.fix?.operator).toBe("where_present");
    for (const numeric of [unit("int"), unit("float")]) {
      expect(
        paletteFor(ctx, operators, numeric).find((item) => item.operator === "add")?.enabled,
        `add over ${spell(numeric)}`,
      ).toBe(true);
    }
  });

  it("requires without_nulls before join over a list whose items may be missing", () => {
    const palette = paletteFor(ctx, operators, array(maybeStr));
    const join = palette.find((item) => item.operator === "join");
    expect(join?.enabled).toBe(false);
    expect(join?.reason).toMatch(/items might be missing/);
    expect(join?.fix?.operator).toBe("without_nulls");
    const drop = palette.find((item) => item.operator === "without_nulls");
    expect(drop?.enabled).toBe(true);
  });

  it("refuses without_nulls when every item already has a value", () => {
    const [drop] = paletteFor(ctx, operators.filter((item) => item.operator === "without_nulls"), array(unit("str")));
    expect(drop?.enabled).toBe(false);
    expect(drop?.reason).toMatch(/nothing to drop/);
  });

  it("only offers join over a list of non-null text", () => {
    const palette = paletteFor(ctx, operators, array(unit("str")));
    expect(palette.find((item) => item.operator === "join")?.enabled).toBe(true);
    expect(palette.find((item) => item.operator === "join")?.arity).toBe(2);
    const ints = paletteFor(ctx, operators, array(unit("int")));
    expect(ints.find((item) => item.operator === "join")?.enabled).toBe(false);
  });

  it("offers pick on a struct that declares a member and refuses one that does not", () => {
    const premises: LogicalType = nullable(structRef(SITES, "PremisesStruct"));
    expect(paletteFor(ctx, operators, premises).find((item) => item.operator === "struct_field")?.enabled).toBe(true);
    const ghost: LogicalType = structRef(SITES, "GhostStruct");
    const pick = paletteFor(ctx, operators, ghost).find((item) => item.operator === "struct_field");
    expect(pick?.enabled).toBe(false);
    expect(pick?.reason).toMatch(/no members|nested record/);
  });

  it("offers map_items only over a list of records, and expand over any list", () => {
    const listOfRecords: LogicalType = nullable(array(nullable(structRef(SITES, "PremisesStruct"))));
    const palette = paletteFor(ctx, operators, listOfRecords);
    expect(palette.find((item) => item.operator === "map_items")?.enabled).toBe(true);
    expect(palette.find((item) => item.operator === "expand")?.enabled).toBe(true);
    expect(paletteFor(ctx, operators, unit("str")).find((item) => item.operator === "expand")?.enabled).toBe(false);
  });

  it("gives `text` to int alone, as IntExpression does", () => {
    expect(paletteFor(ctx, operators, unit("int")).find((item) => item.operator === "text")?.enabled).toBe(true);
    expect(paletteFor(ctx, operators, unit("float")).find((item) => item.operator === "text")?.enabled).toBe(false);
  });

  it("keeps bool logic on bool and comparison on text", () => {
    const bools = paletteFor(ctx, operators, unit("bool")).filter((item) => item.enabled).map((item) => item.operator);
    expect(bools).toEqual(expect.arrayContaining(["not", "and", "or", "keep_if"]));
    expect(bools).not.toContain("equals");
    expect(bools).not.toContain("concat");
  });

  it("groups the palette navigate, effect, calculate, aggregate, compare, logic", () => {
    const groups = [...new Set(paletteFor(ctx, operators, unit("str")).map((item) => item.group))];
    expect(groups.every((group) => ["navigate", "effect", "calculate", "aggregate", "compare", "logic"].includes(group))).toBe(true);
    expect(groups).toContain("effect");
  });

  it("matches shapes the way matches_shape does", () => {
    expect(matchesShape(maybeStr, "nullable")).toBe(true);
    expect(matchesShape(maybeStr, "unit:str")).toBe(false);
    expect(matchesShape(unit("str"), "unit:str")).toBe(true);
    expect(matchesShape(nullable(array(maybeStr)), "array")).toBe(true);
    expect(matchesShape(nullable(array(maybeStr)), "array_of_non_null_str")).toBe(false);
    expect(matchesShape(nullable(structRef(SITES, "PremisesStruct")), "struct")).toBe(true);
  });

  it("starts nothing without a tip", () => {
    const palette = paletteFor(ctx, operators, null);
    expect(palette.every((item) => !item.enabled)).toBe(true);
    expect(palette[0]?.reason).toMatch(/starts by picking a table or projection/);
  });
});

/* ------------------------------------------------------------------------- concat */

describe("concat argument order", () => {
  // Every column in the sample project is nullable, so a non-null text tip has to be
  // made, which is also exactly what an author does in front of a calculation.
  const base: Block[] = [source(["site_id"]), step("where_present")];

  it("writes prepend as [value, self]", () => {
    const prepend = blockFor(entryFor("concat", "prepend"), unit("str"), { text: "SR-" });
    const { expression } = expressionFromBlocks(ctx, [...base, prepend]);
    expect(expression?.kind === "operation" && expression.operator).toBe("concat");
    if (expression?.kind !== "operation") throw new Error("expected concat");
    expect(expression.arguments?.[0]?.kind).toBe("literal");
    expect(expression.arguments?.[1]?.kind).toBe("operation");
    expect(renderPreview(ctx, expression)).toBe('SitesTable.site_id.where_present().expression.prepend("SR-")');
  });

  it("writes append as [self, value]", () => {
    const append = blockFor(entryFor("concat", "append"), unit("str"), { text: "-SR" });
    const { expression } = expressionFromBlocks(ctx, [...base, append]);
    if (expression?.kind !== "operation") throw new Error("expected concat");
    expect(expression.arguments?.[0]?.kind).toBe("operation");
    expect(expression.arguments?.[1]?.kind).toBe("literal");
    expect(renderPreview(ctx, expression)).toBe('SitesTable.site_id.where_present().expression.append("-SR")');
  });

  it("round-trips the side back out of the argument order", () => {
    const prepend = blockFor(entryFor("concat", "prepend"), unit("str"), { text: "SR-" });
    const { expression } = expressionFromBlocks(ctx, [...base, prepend]);
    const blocks = blocksFromExpression(expression);
    const tail = blocks[blocks.length - 1];
    expect(tail?.kind === "operation" && tail.side).toBe("prepend");
  });

  it("renders the two sides as different Python", () => {
    const field: Expression = { kind: "field", source: "sites", path: ["site_name"], logical_type: unit("str") };
    const literal: Expression = { kind: "literal", value: "-", logical_type: unit("str") };
    const prepend: Expression = { kind: "operation", operator: "concat", arguments: [literal, field], parameters: {}, logical_type: unit("str") };
    const append: Expression = { kind: "operation", operator: "concat", arguments: [field, literal], parameters: {}, logical_type: unit("str") };
    // The two sides are the same operator with the arguments swapped, and the Python
    // says which side the written text landed on.
    expect(renderPreview(ctx, prepend)).toBe('SitesTable.site_name.expression.prepend("-")');
    expect(renderPreview(ctx, append)).toBe('SitesTable.site_name.expression.append("-")');
  });
});

/* ---------------------------------------------------------------------------- seams */

describe("type seams", () => {
  it("derives a nullable tip from the flattened index paths", () => {
    expect(tipType(ctx, [source(["site_id"])])).toEqual(maybeStr);
  });

  it("unwraps the nullable at where_present and shows the bare str", () => {
    const blocks: Block[] = [source(["site_id"]), step("where_present")];
    expect(seamsFor(ctx, blocks).types[1]).toEqual(unit("str"));
    expect(tipType(ctx, blocks)).toEqual(unit("str"));
  });

  it("unwraps at coalesce too, and keeps the row", () => {
    const blocks: Block[] = [
      source(["site_name"]),
      step("coalesce", { operands: [{ slot: 1, kind: "literal", value: "Unnamed site", type: unit("str") }] }),
    ];
    expect(tipType(ctx, blocks)).toEqual(unit("str"));
    expect(renderPreview(ctx, expressionFromBlocks(ctx, blocks).expression)).toBe(
      'SitesTable.site_name.default_to("Unnamed site").expression',
    );
  });

  it("refuses a nullable column as the other piece of text, by the self guard", () => {
    const blocks: Block[] = [
      source(["site_name"]),
      step("where_present"),
      step("concat", {
        side: "append",
        operands: [{ slot: 1, kind: "field", source: "equipment", path: ["unit_ref"] }],
      }),
    ];
    // `concat` requires `self` — the same non-null type as the value under it — and
    // every column in this project is nullable, so only a written value can be the other side.
    const { expression, error } = expressionFromBlocks(ctx, blocks);
    expect(expression).toBeNull();
    expect(error).toMatch(/concat needs the other piece of text to be text that is never missing/);
  });

  it("writes a literal operand with the type it was given", () => {
    const blocks: Block[] = [
      source(["site_name"]),
      step("where_present"),
      step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "-x", type: unit("str") }] }),
    ];
    const { expression, error } = expressionFromBlocks(ctx, blocks);
    expect(error).toBeNull();
    const arguments_ = expression?.kind === "operation" ? (expression.arguments ?? []) : [];
    expect(arguments_[0]?.kind).toBe("operation");
    expect(arguments_[1]).toEqual({ kind: "literal", value: "-x", logical_type: unit("str") });
  });

  it("propagates nullability along a folded path, member through a nullable record", () => {
    const type = fieldPathType(ctx, "sites", ["premises", "contact", "location", "city"]);
    expect(type.error).toBeNull();
    expect(type.type).toEqual(maybeStr);
  });

  it("makes a pick through a nullable struct nullable", () => {
    const blocks: Block[] = [
      source(["premises"]),
      step("where_present"),
      step("struct_field", { parameters: { name: "contact_name" } }),
    ];
    expect(tipType(ctx, blocks)).toEqual(maybeStr);
  });

  it("refuses a calculation under a still-nullable seam", () => {
    const blocks: Block[] = [source(["site_id"]), step("equals", { operands: [{ slot: 1, kind: "literal", value: "x", type: unit("str") }] })];
    const seams = seamsFor(ctx, blocks);
    expect(seams.broken?.index).toBe(1);
    expect(seams.broken?.message).toMatch(/never missing/);
    expect(expressionFromBlocks(ctx, blocks).expression).toBeNull();
  });

  it("takes one level off with expand and preserves the item's nullability", () => {
    const blocks: Block[] = [source(["priority_scores"]), step("expand")];
    expect(tipType(ctx, blocks)).toEqual(nullable(unit("int")));
  });

  it("drops item nullability with without_nulls and keeps the list's own", () => {
    const blocks: Block[] = [source(["priority_scores"]), step("without_nulls")];
    expect(tipType(ctx, blocks)).toEqual(nullable(array(unit("int"))));
  });

  it("joins a non-null list to str and a nullable list to str | None", () => {
    const join = (items: LogicalType, nullableList: boolean): LogicalType | null => {
      const list: LogicalType = nullableList ? nullable(array(items)) : array(items);
      const block: Block[] = [
        { id: "l", role: "head", kind: "literal", value: ["a"], type: list },
        step("join", { operands: [{ slot: 1, kind: "literal", value: ", ", type: unit("str") }] }),
      ];
      return tipType(ctx, block);
    };
    expect(join(unit("str"), false)).toEqual(unit("str"));
    expect(join(unit("str"), true)).toEqual(nullable(unit("str")));
  });
});

/* --------------------------------------------------------------------- path folding */

describe("pick folds the path", () => {
  it("reads two struct_field nodes over a field back into one path", () => {
    const expression: Expression = {
      kind: "operation",
      operator: "struct_field",
      arguments: [
        {
          kind: "operation",
          operator: "struct_field",
          arguments: [{ kind: "field", source: "sites", path: ["premises"], logical_type: nullable(structRef(SITES, "PremisesStruct")) }],
          parameters: { name: "contact" },
          logical_type: nullable(structRef(SITES, "PremisesContactStruct")),
        },
      ],
      parameters: { name: "email" },
      logical_type: maybeStr,
    };
    const blocks = blocksFromExpression(expression);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]?.kind === "source" && blocks[0].path).toEqual(["premises", "contact", "email"]);
    // The chain is longer than the generator's 88 columns, so it breaks inside
    // parentheses — one `.pick` per folded path segment either way.
    expect(renderPreview(ctx, expression)).toContain(".pick(lambda value: value.contact)");
    expect(renderPreview(ctx, expression)).toContain(".pick(lambda value: value.email)");
  });

  it("keeps struct_field as a block above an operation", () => {
    const blocks: Block[] = [
      source(["premises"]),
      step("where_present"),
      step("struct_field", { parameters: { name: "contact_name" } }),
    ];
    const expression = expressionFromBlocks(ctx, blocks).expression;
    if (expression?.kind !== "operation") throw new Error("expected an operation");
    expect(expression.operator).toBe("struct_field");
    expect(expression.arguments?.[0]?.kind === "operation" && expression.arguments[0].operator).toBe("where_present");
    expect(renderPreview(ctx, expression)).toBe(
      "SitesTable.premises.where_present().pick(lambda value: value.contact_name).expression",
    );
  });

  it("renders a nested path through two structs as folded picks", () => {
    const blocks: Block[] = [source(["premises", "contact", "location", "city"])];
    const expression = expressionFromBlocks(ctx, blocks).expression;
    if (expression?.kind !== "field") throw new Error("expected a field reference");
    expect(expression.path).toEqual(["premises", "contact", "location", "city"]);
    // 88 columns is the generator's line width; a chain this deep breaks.
    const preview = renderPreview(ctx, expression);
    expect(preview.split("\n").filter((line) => line.includes(".pick(lambda value: value."))).toHaveLength(3);
    expect(preview).toContain("SitesTable.premises");
    expect(preview).toContain("value.city");
    expect(preview).not.toContain("struct_field");
  });

  it("names the struct's members for the pick control", () => {
    const struct: StructType = structRef(SITES, "PremisesStruct");
    expect(structMembers(ctx, struct).map((member) => member.name)).toEqual(["contact_name", "contact"]);
    expect(memberNameOf("contact_name")).toBe("contact_name");
  });
});

/* ------------------------------------------------------------------------- preview */

describe("preview renderer", () => {
  it("freezes temporal literals as canonical text with the real unit", () => {
    expect(literalExpressionText("2026-08-01T12:30:00", unit("timestamp"))).toBe(
      'value_expression(Timestamp.fromisoformat("2026-08-01T12:30:00"))',
    );
    expect(literalExpressionText("2026-08-01", unit("date"))).toBe('value_expression(Date.fromisoformat("2026-08-01"))');
    expect(literalExpressionText("12:30:00", unit("time"))).toBe('value_expression(Time.fromisoformat("12:30:00"))');
  });

  it("types a null literal explicitly, because a null cannot be inferred", () => {
    expect(literalExpressionText(null, maybeStr)).toBe("value_expression(None, logical_type=NullableType(STR))");
    expect(typeObjectText(array(nullable(unit("int"))))).toBe("ArrayType(NullableType(INT))");
    expect(literalExpressionText([], array(unit("str")))).toBe("value_expression([], logical_type=ArrayType(STR))");
    expect(literalExpressionText([null, null], array(maybeStr))).toBe(
      "value_expression([None, None], logical_type=ArrayType(NullableType(STR)))",
    );
    expect(literalExpressionText(["a", "b"], array(unit("str")))).toBe('value_expression(["a", "b"])');
  });

  it("writes plain values where the authoring method accepts them", () => {
    const expression: Expression = {
      kind: "operation",
      operator: "coalesce",
      arguments: [
        { kind: "field", source: "sites", path: ["site_name"], logical_type: maybeStr },
        { kind: "literal", value: null, logical_type: maybeStr },
      ],
      parameters: {},
      logical_type: unit("str"),
    };
    expect(renderPreview(ctx, expression)).toContain(
      "SitesTable.site_name\n    .default_to(value_expression(None, logical_type=NullableType(STR)))",
    );
  });

  it("lowers a selection to an expression before a calculation", () => {
    expect(renderPreview(ctx, renderExpressionOf([source(["site_id"]), step("where_present")]))).toBe(
      "SitesTable.site_id.where_present().expression",
    );
  });

  it("does not double-write .expression after a calculation", () => {
    const expression = renderExpressionOf([
      source(["site_id"]),
      step("where_present"),
      step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] }),
    ]);
    expect(renderPreview(ctx, expression)).toBe('SitesTable.site_id.where_present().expression.append("!")');
  });

  it("keeps the framework's reserved member name escaped", () => {
    expect(memberNameOf("options")).toBe("options_");
    expect(renderField(ctx, "sites", ["a", "options"], unit("str")).parts[1]).toBe(".pick(lambda value: value.options_)");
  });

  const renderExpressionOf = (blocks: Block[]): Expression => {
    const { expression, error } = expressionFromBlocks(ctx, blocks);
    if (!expression) throw new Error(error ?? "no expression");
    return expression;
  };
});

/* ---------------------------------------------------------------------------- keys */

describe("key legality", () => {
  it("refuses a nullable build key in the framework's own words", () => {
    expect(checkKey("build_key", maybeStr)).toMatchObject({
      ok: false,
      message: "build_key must not be nullable, and it resolves to str | None",
      fix: "where_present",
    });
  });

  it("refuses a list or record as a key before it refuses nullability", () => {
    expect(checkKey("source_build_key", array(unit("str"))).message).toMatch(/must be a scalar/);
    expect(checkKey("target_build_key", structRef(SITES, "PremisesStruct")).message).toMatch(/must be a scalar/);
  });

  it("accepts a key once the stack unwraps it", () => {
    const blocks: Block[] = [source(["site_id"]), step("where_present")];
    expect(checkKey("build_key", tipType(ctx, blocks)).ok).toBe(true);
  });
});

/* -------------------------------------------------------------------- slot safety */

describe("slot type safety", () => {
  const slot = (type: LogicalType, name = "city"): ResolvedProperty => ({ name, logical_type: type, optional: false, declared_by: "site" });

  it("shows the mismatch with the expected and actual types", () => {
    const check = checkSlot("SiteNode", slot(unit("str")), unit("int"));
    expect(check.ok).toBe(false);
    expect(check.message).toBe(
      "SiteNode.city expects UnitType(name='str'), but the expression resolves to UnitType(name='int')",
    );
    expect(domainRepr(nullable(array(unit("int"))))).toBe("NullableType(value=ArrayType(item=UnitType(name='int')))");
  });

  it("lets a non-null value satisfy a nullable slot, and not the other way round", () => {
    expect(checkSlot("SiteNode", slot(maybeStr), unit("str")).ok).toBe(true);
    expect(compatible(maybeStr, unit("str"))).toBe(true);
    expect(compatible(unit("str"), maybeStr)).toBe(false);
    expect(checkSlot("SiteNode", slot(unit("str")), maybeStr).ok).toBe(false);
  });
});

/* ---------------------------------------------------------------------- endpoints */

describe("endpoint requirement", () => {
  it("is silent for a node component", () => {
    expect(endpointSides(ctx, "site")).toEqual([]);
  });

  it("is silent when the declaration names concrete components", () => {
    const sides = endpointSides(ctx, "has_unit");
    expect(sides).toHaveLength(2);
    expect(sides.every((side) => !side.required)).toBe(true);
  });

  it("demands a token per side once the declared endpoint is a category", () => {
    const withCategory: BindingContext = {
      ...ctx,
      document: {
        ...ctx.document,
        components: [
          ...(ctx.document.components ?? []),
          {
            id: "observed_during",
            kind: "edge",
            tier: "concrete",
            declaration_name: "ObservedDuringEdge",
            name: "observed_during",
            parent: "monitored_relation",
            source: "site",
            target: "documented",
            properties: [],
          },
        ],
      },
    };
    const sides = endpointSides(withCategory, "observed_during");
    expect(sides.find((side) => side.side === "source")?.required).toBe(false);
    const target = sides.find((side) => side.side === "target");
    expect(target?.required).toBe(true);
    expect(target?.category).toBe("DocumentedAbstractNode");
    expect(target?.options.map((option) => option.value)).toEqual(["site", "unit"]);
  });

  it("only offers concrete components that descend from the category", () => {
    expect(concreteDescendants(ctx, "documented").map((item) => item.value)).toEqual(["site", "unit"]);
    expect(concreteDescendants(ctx, "documented").some((item) => item.value === "documented")).toBe(false);
  });
});

/* ----------------------------------------------------------------- block operations */

describe("deletion cascade", () => {
  const stack: Block[] = [
    source(["site_id"]),
    step("where_present"),
    step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] }),
    step("equals", { operands: [{ slot: 1, kind: "literal", value: "x", type: unit("str") }] }),
  ];

  it("says which downstream blocks a deletion takes with it", () => {
    const { blocks, removed } = removeBlock(ctx, stack, 1);
    expect(removed.map((block) => block.kind === "operation" ? block.operator : block.kind)).toEqual([
      "where_present",
      "concat",
      "equals",
    ]);
    expect(blocks).toHaveLength(1);
  });

  it("repairs rather than deletes when the downstream stack still types", () => {
    const keepable: Block[] = [
      source(["site_id"]),
      step("where_present"),
      step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] }),
    ];
    const { blocks, removed } = removeBlock(ctx, keepable, 2);
    expect(removed).toHaveLength(1);
    expect(blocks).toHaveLength(2);
    expect(tipType(ctx, blocks)).toEqual(unit("str"));
  });

  it("never deletes the source block", () => {
    const { blocks, removed } = removeBlock(ctx, stack, 0);
    expect(removed).toEqual([]);
    expect(blocks).toBe(stack);
  });
});

describe("reordering", () => {
  it("refuses to move an effect block below the block that needs its output", () => {    const blocks: Block[] = [
      source(["site_id"]),
      step("where_present"),
      step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] }),
    ];
    const { blocks: unchanged, reason } = moveBlocks(ctx, blocks, 1, 2);
    expect(unchanged).toBe(blocks);
    expect(reason).toMatch(/Keep rows where present cannot move below Put text behind/);
  });

  it("refuses to move anything above the source", () => {
    const blocks: Block[] = [source(["site_id"]), step("where_present")];
    expect(moveBlocks(ctx, blocks, 1, 0).reason).toMatch(/below the source/);
    expect(moveBlocks(ctx, blocks, 0, 1).reason).toMatch(/stays at the top/);
  });

  it("allows a reorder that still type-checks, and refuses one that does not", () => {
    const blocks: Block[] = [
      source(["site_id"]),
      step("where_present"),
      step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] }),
      step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "?", type: unit("str") }] }),
    ];
    const { blocks: moved, reason } = moveBlocks(ctx, blocks, 2, 3);
    expect(reason).toBeNull();
    expect(moved[3]?.kind === "operation" && moved[3].operands[0]?.kind).toBe("literal");
    expect(seamsFor(ctx, moved).broken).toBeNull();
    // Two text blocks can swap; a text block cannot move under a comparison, which
    // answers bool rather than text.
    const withBool: Block[] = [...blocks.slice(0, 3), step("equals", { operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] })];
    expect(moveBlocks(ctx, withBool, 2, 3).reason).toMatch(/cannot move below/);
  });
});

/* ---------------------------------------------------------------------- binding list */

describe("binding identity and slots", () => {
  it("derives a unique id and allows a second binding for one component", () => {
    expect(bindingIdFor("site", [])).toBe("site_binding");
    expect(bindingIdFor("site", ["site_binding"])).toBe("site_binding_2");
    expect(bindingIdFor("site", ["site_binding", "site_binding_2"])).toBe("site_binding_3");
  });

  it("lists the slots a binding still owes, inherited ones included", () => {
    const binding = (ctx.document.bindings ?? [])[0] as Binding;
    const owed = unboundSlots(ctx, binding).map((slot) => slot.name);
    expect(owed).toContain("summary");
  });

  it("resolves inherited slots in the order the generated record has them", () => {
    const slots = resolvedSlots(ctx, "site");
    // Own slots first, then the category's, then the mixin's: the order the generated
    // record exposes (`SiteNode` reads name, city, summary, source_version).
    expect(slots.map((slot) => slot.name)).toEqual(["name", "city", "summary", "source_version"]);
    expect(slots.find((slot) => slot.name === "summary")?.declared_by).toBe("documented");
    // Types come from the index, which is where the backend already resolved them.
    expect(slots.find((slot) => slot.name === "city")?.logical_type).toEqual(unit("str"));
  });
});

/* ------------------------------------------------------- refusal wording and reseating */

describe("why a block is unavailable", () => {
  it("blames nullability only when an unwrap is what is missing", () => {
    const concat = paletteFor(ctx, operators, maybeStr).find((item) => item.operator === "concat");
    expect(concat?.enabled).toBe(false);
    expect(concat?.reason).toMatch(/needs a non-null str — add Keep rows where present/);
    expect(concat?.fix?.operator).toBe("where_present");
  });

  it("does not offer an unwrap that would not help, when the kind itself is wrong", () => {
    const text = paletteFor(ctx, operators, array(maybeStr)).find((item) => item.operator === "text");
    expect(text?.enabled).toBe(false);
    expect(text?.reason).toMatch(/needs int; this tip is Array\[str \| None\]/);
    expect(text?.fix).toBeNull();
  });

  it("says what a list of records means when the tip is a single record", () => {
    const mapItems = paletteFor(ctx, operators, nullable(structRef(SITES, "PremisesStruct"))).find(
      (item) => item.operator === "map_items",
    );
    expect(mapItems?.enabled).toBe(false);
    expect(mapItems?.reason).toMatch(/every record in a list/);
    expect(mapItems?.reason).not.toMatch(/non-null/);
  });

  it("only offers the drop-items fix over a list whose items may be missing", () => {
    const overText = paletteFor(ctx, operators, maybeStr).find((item) => item.operator === "join");
    expect(overText?.enabled).toBe(false);
    expect(overText?.fix).toBeNull();
    const overNullableItems = paletteFor(ctx, operators, array(maybeStr)).find((item) => item.operator === "join");
    expect(overNullableItems?.enabled).toBe(false);
    expect(overNullableItems?.reason).toMatch(/add Drop missing items first/);
    expect(overNullableItems?.fix?.operator).toBe("without_nulls");
  });
});

describe("re-pointing the source block", () => {
  it("drops the blocks the new value no longer feeds, and says so", () => {
    const blocks: Block[] = [
      source(["priority_scores"]),
      step("without_nulls"),
      step("expand"),
    ];
    const { blocks: next, dropped } = reseatHead(ctx, blocks, source(["site_name"]));
    expect(next).toHaveLength(1);
    expect(dropped.map((block) => (block as OperationBlock).operator)).toEqual(["without_nulls", "expand"]);
    expect(tipType(ctx, next)).toEqual(maybeStr);
  });

  it("keeps the whole stack when the new column has the same type", () => {
    const blocks: Block[] = [source(["site_id"]), step("where_present")];
    const { blocks: next, dropped } = reseatHead(ctx, blocks, source(["site_name"]));
    expect(dropped).toEqual([]);
    expect(next).toHaveLength(2);
    expect(tipType(ctx, next)).toEqual(unit("str"));
  });

  it("never drops the source block itself, even when nothing fits", () => {
    const blocks: Block[] = [source(["site_id"]), step("where_present"), step("concat", { side: "append", operands: [{ slot: 1, kind: "literal", value: "!", type: unit("str") }] })];
    const { blocks: next, dropped } = reseatHead(ctx, blocks, source(["premises", "contact", "location", "room"]));
    expect(next[0]?.role).toBe("head");
    expect(dropped.length).toBeLessThan(blocks.length);
  });
});
