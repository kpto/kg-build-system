import { describe, expect, it } from "vitest";

import { array, emptyDocument, nullable, structRef, unit, type Binding, type Expression, type ProjectDocument, type Projection, type Source, type Struct, type Table } from "@/lib/ir";
import { SAMPLE_DOCUMENT } from "@/lib/sampleDocument";
import type { InferResponse } from "@/lib/types";

import {
  addMemberToGroup,
  applyImportPreview,
  buildImportPreview,
  catalogPath,
  chainSummary,
  drivingSource,
  canAddOutput,
  expressionSources,
  isGroupDeclaration,
  isGroupOnly,
  isTableGroup,
  memberTables,
  offlineImportPreview,
  outputReaders,
  referrersForDeletion,
  referrersOfProjection,
  referencedStructQualnames,
  reorderFields,
  resolveGroupSourcePaths,
  shapeProvenance,
  suggestDeclarationName,
  suggestId,
  trustAllowsNonNull,
  trustTier,
} from "./logic";

const maybeStr = nullable(unit("str"));

/* --------------------------------------------------------------------- naming */

describe("id / declaration_name suggestion", () => {
  it("snake-cases a label and adds the free-id suffix while it is taken", () => {
    expect(suggestId("Breast cancer targets", [])).toBe("breast_cancer_targets");
    expect(suggestId("sites", ["sites", "sites_2"])).toBe("sites_3");
  });

  it("strips a trailing tier suffix so a table never renders SitesTableTable", () => {
    expect(suggestId("Sites Table", [])).toBe("sites");
    expect(suggestId("Publications TableGroup", [])).toBe("publications");
  });

  it("renders the exact class name the generator emits per section", () => {
    expect(suggestDeclarationName("table", "sites")).toBe("SitesTable");
    expect(suggestDeclarationName("table", "publications", true)).toBe("PublicationsTableGroup");
    expect(suggestDeclarationName("struct", "premises_contact")).toBe("PremisesContactStruct");
    expect(suggestDeclarationName("projection", "site_cities")).toBe("SiteCitiesProjection");
  });
});

/* --------------------------------------------------------- referrer analysis */

describe("referrer analysis", () => {
  it("blocks deleting a struct that a table field reads, naming the referrer", () => {
    const referrers = referrersForDeletion(SAMPLE_DOCUMENT, "struct", "premises");
    expect(referrers.map((item) => item.ref)).toContain("table:sites");
    expect(referrers[0]?.label).toBe("sites.premises");
  });

  it("blocks deleting a table bound by a source and owned by a group", () => {
    const referrers = referrersForDeletion(SAMPLE_DOCUMENT, "table", "temperature_readings");
    const kinds = new Set(referrers.map((item) => item.kind));
    expect(kinds).toContain("group"); // readings owns it as a member
    expect(referrers.map((item) => item.ref)).toContain("table:readings");
  });

  it("blocks deleting a projection a binding reads, and reports a clean entity as clean", () => {
    const document: ProjectDocument = {
      ...SAMPLE_DOCUMENT,
      bindings: [
        ...(SAMPLE_DOCUMENT.bindings ?? []),
        {
          id: "city_binding",
          kind: "node",
          component: "site",
          build_key: { kind: "field", source: "site_cities", path: ["site_id"], logical_type: maybeStr },
          properties: [],
        },
      ],
    };
    const referrers = referrersForDeletion(document, "projection", "site_cities");
    expect(referrers.map((item) => item.ref)).toContain("binding:city_binding.build_key");
    expect(referrersForDeletion(SAMPLE_DOCUMENT, "projection", "site_cities")).toEqual([]);
  });

  it("names each blocking referrer by its own stack, not by a shared component", () => {
    // Two bindings writing one component would otherwise print the same word twice in
    // the dialog that is supposed to say which reference to go and break.
    const document: ProjectDocument = {
      ...SAMPLE_DOCUMENT,
      bindings: [
        {
          id: "first_binding",
          kind: "node",
          component: "site",
          build_key: { kind: "field", source: "site_cities", path: ["site_id"], logical_type: maybeStr },
          properties: [],
        },
        {
          id: "second_binding",
          kind: "node",
          component: "site",
          build_key: { kind: "literal", value: "x", logical_type: unit("str") },
          properties: [
            { name: "city", expression: { kind: "field", source: "site_cities", path: ["city"], logical_type: maybeStr } },
          ],
        },
      ],
    };

    const labels = referrersForDeletion(document, "projection", "site_cities").map((item) => item.label);
    expect(labels).toContain("first_binding.build_key");
    expect(labels).toContain("second_binding.property.city");
    expect(new Set(labels).size).toBe(2);
  });
});

/* ------------------------------------------------- consumers of one projection output */

describe("projection output consumers", () => {
  const field = (source: string, path: string[]): Expression => ({
    kind: "field",
    source,
    path,
    logical_type: maybeStr,
  });
  const nodeBinding = (
    id: string,
    buildKey: Expression,
    properties: { name: string; expression: Expression }[] = [],
  ): Binding => ({ id, kind: "node", component: "site", build_key: buildKey, properties });

  // `site_cities` carries two outputs, so the consumers of one output must never be
  // offered as the consumers of the other.
  const siteCities = SAMPLE_DOCUMENT.projections?.[0] as Projection;
  const refs = (document: ProjectDocument, outputName: string) =>
    outputReaders(document, siteCities, outputName).map((item) => item.ref);
  const withBindings = (bindings: Binding[]): ProjectDocument => ({
    ...SAMPLE_DOCUMENT,
    bindings: [...(SAMPLE_DOCUMENT.bindings ?? []), ...bindings],
  });

  it("names the stack that reads the output, addressed at the stack rather than the binding", () => {
    expect(refs(withBindings([nodeBinding("studied_in_binding", field("site_cities", ["site_id"]))]), "site_id")).toEqual([
      "binding:studied_in_binding.build_key",
    ]);
    const propertyStack = nodeBinding("studied_in_binding", field("sites", ["site_id"]), [
      { name: "city", expression: field("site_cities", ["site_id"]) },
    ]);
    expect(refs(withBindings([propertyStack]), "site_id")).toEqual(["binding:studied_in_binding.property.city"]);
  });

  it("keeps each output of a multi-output projection pointed at its own consumer", () => {
    const document = withBindings([
      nodeBinding("ids_only_binding", field("site_cities", ["site_id"])),
      nodeBinding("scores_only_binding", field("site_cities", ["score"])),
    ]);
    expect(refs(document, "site_id")).toEqual(["binding:ids_only_binding.build_key"]);
    expect(refs(document, "score")).toEqual(["binding:scores_only_binding.build_key"]);
  });

  it("ignores a source that only shares the projection's name as a prefix", () => {
    expect(refs(withBindings([nodeBinding("lookalike_binding", field("site_cities_legacy", ["site_id"]))]), "site_id")).toEqual([]);
  });

  it("ignores an output whose name only starts with the one asked for", () => {
    expect(refs(withBindings([nodeBinding("longer_binding", field("site_cities", ["site_id_legacy"]))]), "site_id")).toEqual([]);
  });

  it("finds the reference buried in a stack's operation arguments", () => {
    const wrapped: Expression = {
      kind: "operation",
      operator: "concat",
      arguments: [
        { kind: "literal", value: "S-", logical_type: unit("str") },
        {
          kind: "operation",
          operator: "where_present",
          arguments: [field("site_cities", ["site_id"])],
          parameters: {},
          logical_type: unit("str"),
        },
      ],
      parameters: {},
      logical_type: unit("str"),
    };
    expect(refs(withBindings([nodeBinding("wrapped_binding", wrapped)]), "site_id")).toEqual([
      "binding:wrapped_binding.build_key",
    ]);
  });

  it("excludes a projection reading the projection, which the delete-impact list keeps", () => {
    const reader: Projection = {
      id: "site_labels",
      declaration_name: "SiteLabelsProjection",
      name: "site_labels",
      fields: [{ name: "label", expression: field("site_cities", ["site_id"]) }],
    };
    const document: ProjectDocument = {
      ...withBindings([nodeBinding("studied_in_binding", field("site_cities", ["site_id"]))]),
      projections: [...(SAMPLE_DOCUMENT.projections ?? []), reader],
    };
    expect(refs(document, "site_id")).toEqual(["binding:studied_in_binding.build_key"]);
    expect(referrersOfProjection(document, siteCities).map((item) => item.ref)).toContain(
      "projection:site_labels.field.label",
    );
  });

  it("lists every stack reading one output, in document order", () => {
    const document = withBindings([
      nodeBinding("zeta_binding", field("sites", ["site_id"]), [
        { name: "city", expression: field("site_cities", ["site_id"]) },
      ]),
      nodeBinding("alpha_binding", field("site_cities", ["site_id"])),
    ]);
    expect(refs(document, "site_id")).toEqual([
      "binding:zeta_binding.property.city",
      "binding:alpha_binding.build_key",
    ]);
  });

  it("reports no consumers for an output nothing reads", () => {
    expect(outputReaders(SAMPLE_DOCUMENT, siteCities, "site_id")).toEqual([]);
  });
});

/* --------------------------------------------------- group membership invariants */

describe("group membership invariants", () => {
  const group: Table = { id: "publications", declaration_name: "PublicationsTableGroup", name: "publications", fields: [], members: [], group: null };
  const clinical: Table = { id: "clinical", declaration_name: "ClinicalTable", name: "clinical", fields: [{ name: "publication_id", logical_type: maybeStr }], group: null };
  const base: ProjectDocument = { ...emptyDocument(), tables: [group, clinical] };

  it("adds a member and sets its group id in both directions", () => {
    const result = addMemberToGroup(base, "publications", "clinical");
    expect(result.ok).toBe(true);
    const next = result.document as ProjectDocument;
    const saved = next.tables?.find((item) => item.id === "clinical");
    const savedGroup = next.tables?.find((item) => item.id === "publications");
    expect(saved?.group).toBe("publications");
    expect(savedGroup?.members).toEqual([{ python_name: "clinical", ref: "clinical" }]);
  });

  it("refuses a duplicate member, self-membership, and a cycle", () => {
    const once = addMemberToGroup(base, "publications", "clinical").document as ProjectDocument;
    expect(addMemberToGroup(once, "publications", "clinical").ok).toBe(false);
    expect(addMemberToGroup(base, "publications", "publications").ok).toBe(false);
    // clinical is now under publications; adding publications to clinical would loop.
    expect(addMemberToGroup(once, "clinical", "publications").ok).toBe(false);
  });

  it("recognises a catalogue-only group versus a member table that kept copied members", () => {
    const populated = addMemberToGroup(base, "publications", "clinical").document as ProjectDocument;
    const groupTable = populated.tables?.find((item) => item.id === "publications") as Table;
    expect(isTableGroup(groupTable)).toBe(true);
    expect(isGroupOnly(groupTable)).toBe(true); // a catalogue owns members and reads nothing
    const copied: Table = { ...clinical, members: [{ python_name: "x", ref: "clinical" }] };
    expect(isTableGroup(copied)).toBe(true);
    expect(isGroupOnly(copied)).toBe(false); // it has fields, so it is readable
  });

  it("treats a freshly-authored empty group as a group by its declaration name", () => {
    // isGroupOnly needs members; isGroupDeclaration captures authoring intent so an
    // empty group still opens its catalogue editor instead of a field grid.
    expect(isGroupOnly(group)).toBe(false); // no members yet
    expect(isGroupDeclaration(group)).toBe(true); // ...TableGroup declaration
    expect(isGroupDeclaration(clinical)).toBe(false);
  });

  it("walks the parent chain to a catalogue path and resolves each member's layout", () => {
    expect(catalogPath(SAMPLE_DOCUMENT, { ...clinical, group: "readings" } as Table)).toEqual(["readings", "clinical"]);
    const readingsGroup = SAMPLE_DOCUMENT.tables?.find((item) => item.id === "readings") as Table;
    expect(memberTables(SAMPLE_DOCUMENT, readingsGroup).map((item) => item.name).sort()).toEqual(["mechanical", "temperature"]);
    const source: Source = { id: "readings_source", table: "readings", location: "data", format: "json", layout: "{group_path}/{table_name}.json" };
    const resolved = resolveGroupSourcePaths(SAMPLE_DOCUMENT, source).map((item) => item.path);
    expect(resolved).toContain("data/readings/temperature.json");
    expect(resolved).toContain("data/readings/mechanical/vibration.json");
  });
});

/* ------------------------------------------------- single-driving-source derive */

describe("single driving source", () => {
  const field = (source: string, path: string[] = ["x"]): Expression => ({ kind: "field", source, path, logical_type: maybeStr });
  const projection = (fields: Expression[]): Projection => ({
    id: "p",
    declaration_name: "PProjection",
    name: "p",
    fields: fields.map((expression, index) => ({ name: `o${index}`, expression })),
  });

  it("derives the driving source from the outputs' field references", () => {
    expect(drivingSource(projection([field("sites"), field("sites", ["premises", "contact"])])).driving).toBe("sites");
    expect(expressionSources(field("sites"))).toEqual(["sites"]);
  });

  it("flags a projection that reads two sources as a conflict", () => {
    const result = drivingSource(projection([field("sites"), field("equipment")]));
    expect(result.conflict).toBe(true);
    expect(result.count).toBe(2);
  });

  it("allows a literal or a same-source output, blocks a second source", () => {
    const sitesTable: Table = { id: "t", declaration_name: "T", name: "sites", fields: [], group: null };
    const document: ProjectDocument = { ...emptyDocument(), tables: [sitesTable] };
    const p = projection([field("sites")]);
    const literal: Expression = { kind: "literal", value: "x", logical_type: unit("str") };
    expect(canAddOutput(document, p, literal).ok).toBe(true);
    expect(canAddOutput(document, p, field("equipment")).ok).toBe(false);
  });
});

/* --------------------------------------------------------------- chain summary */

describe("chain summary rendering", () => {
  it("reads a projection output left to right with expand and struct picks", () => {
    const participants = SAMPLE_DOCUMENT.projections?.[0];
    // sample_cities outputs are plain fields; build the pathways example inline.
    const molecule = SAMPLE_DOCUMENT; // ref not needed
    void participants;
    void molecule;
    const steps = { kind: "field" as const, source: "pathways", path: ["steps"], logical_type: array(nullable(structRef("", "StepsStruct"))) };
    const pickParticipants: Expression = { kind: "operation", operator: "struct_field", arguments: [{ kind: "operation", operator: "expand", arguments: [steps], parameters: {}, logical_type: nullable(structRef("", "StepsStruct")) }], parameters: { name: "participants" }, logical_type: nullable(structRef("", "StepsParticipantsStruct")) };
    const expandParticipants: Expression = { kind: "operation", operator: "expand", arguments: [pickParticipants], parameters: {}, logical_type: nullable(structRef("", "StepsParticipantsStruct")) };
    const role: Expression = { kind: "operation", operator: "struct_field", arguments: [expandParticipants], parameters: { name: "role" }, logical_type: maybeStr };
    expect(chainSummary(role)).toBe("pathways.steps ▸ expand ▸ struct_field(participants) ▸ expand ▸ struct_field(role)");
  });

  it("renders a plain field and a coalesce with its literal", () => {
    expect(chainSummary({ kind: "field", source: "sites", path: ["site_id"], logical_type: maybeStr })).toBe("sites.site_id");
    expect(chainSummary({ kind: "operation", operator: "coalesce", arguments: [{ kind: "field", source: "sites", path: ["name"], logical_type: maybeStr }, { kind: "literal", value: "x", logical_type: unit("str") }], parameters: {}, logical_type: unit("str") })).toBe('sites.name ▸ coalesce("x")');
  });
});

/* ------------------------------------------------------------ trust semantics */

describe("nullability trust-tier semantics", () => {
  it("labels each tier with what it permits", () => {
    expect(trustTier("declared").renders).toBe("Field[X]");
    expect(trustTier("defaulted").renders).toBe("Field[X | None]");
    expect(trustTier(undefined).value).toBe("defaulted");
  });

  it("only lets declared/enforced claim a non-null type", () => {
    expect(trustAllowsNonNull(unit("str"), "defaulted")).toBe(false);
    expect(trustAllowsNonNull(unit("str"), "declared")).toBe(true);
    expect(trustAllowsNonNull(unit("str"), "enforced")).toBe(true);
    expect(trustAllowsNonNull(nullable(unit("str")), "defaulted")).toBe(true);
  });
});

/* ------------------------------------------------------- field reorder (immutable) */

describe("field reorder immutability", () => {
  it("moves an item without mutating the source array", () => {
    const fields = ["a", "b", "c", "d"] as const;
    const next = reorderFields(fields, 0, 2);
    expect(next).toEqual(["b", "c", "a", "d"]);
    expect(fields).toEqual(["a", "b", "c", "d"]);
  });

  it("returns a copy untouched on an out-of-range or no-op move", () => {
    const fields = [{ id: 1 }, { id: 2 }];
    expect(reorderFields(fields, 5, 0)).toEqual(fields);
    expect(reorderFields(fields, 1, 1)).toEqual(fields);
  });
});

/* --------------------------------------------------------------- import preview */

describe("import preview shape", () => {
  const tables: Table[] = [
    { id: "targets", declaration_name: "TargetsTable", name: "targets", fields: [{ name: "target_id", logical_type: maybeStr, schema_path: "target_id" }], group: null },
    { id: "sites", declaration_name: "DupTable", name: "sites", fields: [], group: null },
  ];
  const structs: Struct[] = [{ id: "s_attributes", declaration_name: "AttributesStruct", name: "attributes", fields: [] }];
  const response: InferResponse = { tables, structs, notes: ["1 note"] };
  const sitesExisting = tables[1] as Table;
  const attributesExisting = structs[0] as Struct;

  it("separates new declarations from ones already present", () => {
    const existing: ProjectDocument = { ...emptyDocument(), tables: [sitesExisting], structs: [attributesExisting] };
    const preview = buildImportPreview(response, existing, "data/targets.json", "table");
    expect(preview.newTables.map((item) => item.id)).toEqual(["targets"]);
    expect(preview.existingTableIds).toEqual(["sites"]);
    expect(preview.existingStructIds).toEqual(["s_attributes"]);
    expect(preview.totalNew).toBe(1);
  });

  it("applies only the new tables/structs, leaving existing declarations alone", () => {
    const existing: ProjectDocument = { ...emptyDocument(), tables: [sitesExisting], structs: [] };
    const preview = buildImportPreview(response, existing, "data/targets.json", "table");
    const next = applyImportPreview(existing, preview);
    expect(next.tables?.map((item) => item.id)).toEqual(["sites", "targets"]);
    expect(next.structs?.map((item) => item.id)).toEqual(["s_attributes"]);
  });

  it("falls back to an offline sample shape when the backend is unreachable", () => {
    // `targets` is a canned offline feed the sample document does not yet declare.
    const preview = offlineImportPreview(SAMPLE_DOCUMENT, "data/targets.json", "table");
    expect(preview?.newTables.map((item) => item.id)).toEqual(["targets"]);
    expect(preview?.newStructs.map((item) => item.id)).toContain("attributes_curator");
    // `equipment` is already in the sample document → it reads as existing, not new.
    const dup = offlineImportPreview(SAMPLE_DOCUMENT, "data/equipment.json", "table");
    expect(dup?.newTables).toEqual([]);
    expect(dup?.existingTableIds).toEqual(["equipment"]);
    expect(offlineImportPreview(SAMPLE_DOCUMENT, "data/does_not_exist.json", "table")).toBeNull();
  });
});

/* ------------------------------------------------------------- provenance + refs */

describe("provenance and reference helpers", () => {
  it("marks an inferred table (schema paths) with its bound feed", () => {
    const document: ProjectDocument = {
      ...emptyDocument(),
      tables: [{ id: "targets", declaration_name: "TargetsTable", name: "targets", fields: [{ name: "symbol", logical_type: maybeStr, schema_path: "symbol" }], group: null }],
      sources: [{ id: "targets_source", table: "targets", location: "data/targets.json", format: "json" }],
    };
    const targetsTable = document.tables![0] as Table;
    expect(shapeProvenance(document, targetsTable)).toEqual({ inferred: true, feed: "data/targets.json" });
    // The sample document authored sites by hand (empty schema_path) → not inferred.
    const sites = SAMPLE_DOCUMENT.tables?.find((item) => item.id === "sites") as Table;
    expect(shapeProvenance(SAMPLE_DOCUMENT, sites).inferred).toBe(false);
  });

  it("names the file a group member reads, not the directory its group source points at", () => {
    const base = JSON.parse(JSON.stringify(SAMPLE_DOCUMENT)) as ProjectDocument;
    const member = base.tables?.find((item) => item.id === "temperature_readings") as Table;
    // A non-empty schema_path is what marks a shape as inferred rather than authored.
    const fields = member.fields ?? [];
    const inferredMember: Table = { ...member, fields: [{ ...fields[0]!, schema_path: "deg_c" }] };
    const document: ProjectDocument = {
      ...base,
      tables: (base.tables ?? []).map((item) => (item.id === inferredMember.id ? inferredMember : item)),
      sources: [
        ...(base.sources ?? []),
        {
          id: "readings_source",
          table: "readings",
          location: "data",
          format: "json",
          layout: "{group_path}/{table_name}.json",
        },
      ],
    };
    // The group source's own location is a directory, so a member cannot show it as-is.
    expect(shapeProvenance(document, inferredMember)).toEqual({
      inferred: true,
      feed: "data/readings/temperature.json",
    });
  });

  it("reaches transitively referenced structs through nested struct fields", () => {
    const premises = SAMPLE_DOCUMENT.tables?.find((item) => item.id === "sites") as Table;
    const reachable = referencedStructQualnames(SAMPLE_DOCUMENT, premises.fields ?? []);
    expect(reachable).toContain("PremisesStruct");
    expect(reachable).toContain("PremisesContactLocationStruct");
  });
});
