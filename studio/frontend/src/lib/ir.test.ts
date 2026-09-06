import { describe, expect, it } from "vitest";

import {
  array,
  describeRef,
  emptyDocument,
  expressionSummary,
  nullable,
  sourceBindsTable,
  structRef,
  tableAncestry,
  typeLabel,
  unit,
  type LogicalType,
  type OperationExpression,
  type ProjectDocument,
} from "@/lib/ir";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";

const maybe = (value: Parameters<typeof nullable>[0]): LogicalType => nullable(value);

describe("typeLabel", () => {
  it("renders the canonical spellings the UI shows", () => {
    expect(typeLabel(unit("str"))).toBe("str");
    expect(typeLabel(maybe(unit("str")))).toBe("str | None");
    expect(typeLabel(array(unit("int")))).toBe("Array[int]");
    expect(typeLabel(array(maybe(unit("int"))))).toBe("Array[int | None]");
    expect(typeLabel(maybe(array(maybe(unit("int")))))).toBe("Array[int | None] | None");
    expect(typeLabel(structRef("kg_project.table.sites", "PremisesStruct"))).toBe(
      "Struct{PremisesStruct}",
    );
    expect(typeLabel(maybe(array(structRef("m", "PremisesContactStruct"))))).toBe(
      "Array[Struct{PremisesContactStruct}] | None",
    );
  });

  it("degrades instead of throwing on nothing and on unknown kinds", () => {
    expect(typeLabel(null)).toBe("");
    expect(typeLabel(undefined)).toBe("");
    expect(typeLabel({ kind: "nonsense" } as unknown as LogicalType)).toBe("unknown");
  });

  it("renders the sample document's own types", () => {
    const scores = SAMPLE_DOCUMENT.tables?.[0]?.fields?.[3]?.logical_type;
    expect(typeLabel(scores)).toBe("Array[int | None] | None");
  });
});

describe("expressionSummary", () => {
  const field = (source: string, path: string[], type: LogicalType) => ({
    kind: "field" as const,
    source,
    path,
    logical_type: type,
  });

  const op = (operator: string, args: OperationExpression["arguments"], parameters = {}): OperationExpression => ({
    kind: "operation",
    operator,
    arguments: args ?? [],
    parameters,
    logical_type: unit("str"),
  });

  it("names the source and path of a field reference", () => {
    expect(expressionSummary(field("sites", ["site_id"], maybe(unit("str"))))).toBe("sites.site_id");
    expect(
      expressionSummary(
        field("sites", ["premises", "contact", "location", "city"], maybe(unit("str"))),
      ),
    ).toBe("sites.premises.contact.location.city");
  });

  it("reads a unary operation as a pipeline step", () => {
    expect(
      expressionSummary(op("where_present", [field("sites", ["site_id"], maybe(unit("str")))])),
    ).toBe("sites.site_id → where present");
  });

  it("renders parameters and literal arguments inline", () => {
    expect(
      expressionSummary(
        op("coalesce", [
          field("sites", ["site_name"], maybe(unit("str"))),
          { kind: "literal", value: "Unnamed site", logical_type: unit("str") },
        ]),
      ),
    ).toBe('sites.site_name → default to("Unnamed site")');

    expect(
      expressionSummary(
        op("struct_field", [field("sites", ["premises"], maybe(structRef("m", "PremisesStruct")))], {
          name: "contact",
        }),
      ),
    ).toBe("sites.premises → pick(contact)");
  });

  it("summarises the sample document's real bindings and truncates long trees", () => {
    const binding = SAMPLE_DOCUMENT.bindings?.[0];
    const name = binding?.properties?.[0];
    expect(name && expressionSummary(name.expression)).toBe(
      'sites.site_name → default to("Unnamed site")',
    );
    const deep = op("and", [
      op("and", [op("and", [op("and", [op("not", [op("not", [{ kind: "literal", value: true, logical_type: unit("bool") }])])])])]),
      { kind: "literal", value: true, logical_type: unit("bool") },
    ]);
    expect(expressionSummary(deep).length).toBeLessThanOrEqual(96);
    expect(expressionSummary(null)).toBe("?");
  });
});

describe("describeRef", () => {
  it("addresses a document by ref and reports null for a dangling one", () => {
    const summary = describeRef(SAMPLE_DOCUMENT, "component:site.property.city");
    expect(summary?.title).toBe("site");
    expect(summary?.kind).toBe("node concrete");
    expect(summary?.children.map((child) => child.ref)).toContain(
      "component:site.property.city",
    );
    expect(describeRef(SAMPLE_DOCUMENT, "component:nope")).toBeNull();
    expect(describeRef(emptyDocument() as ProjectDocument, "table:sites")).toBeNull();
  });
});

describe("tableAncestry", () => {
  it("walks a member up through every group above it, nearest first", () => {
    const tables = SAMPLE_DOCUMENT.tables ?? [];
    const vibration = tables.find((item) => item.id === "vibration_readings");
    expect(vibration).toBeDefined();
    expect(tableAncestry(tables, vibration!).map((item) => item.name)).toEqual([
      "vibration",
      "mechanical",
      "readings",
    ]);
  });

  it("stops at a table with no group and at a cycle", () => {
    const tables = SAMPLE_DOCUMENT.tables ?? [];
    const sites = tables.find((item) => !item.group)!;
    expect(tableAncestry(tables, sites).map((item) => item.id)).toEqual([sites.id]);

    const a = { ...sites, id: "a", name: "a", group: "b" };
    const b = { ...sites, id: "b", name: "b", group: "a" };
    expect(tableAncestry([a, b] as never, a).map((item) => item.id)).toEqual(["a", "b"]);
  });

  it("matches a source by table id or by declared name", () => {
    const tables = SAMPLE_DOCUMENT.tables ?? [];
    const member = tables.find((item) => item.id === "temperature_readings")!;
    expect(sourceBindsTable({ table: "temperature" }, member)).toBe(true);
    expect(sourceBindsTable({ table: "temperature_readings" }, member)).toBe(true);
    expect(sourceBindsTable({ table: "readings" }, member)).toBe(false);
  });
});
