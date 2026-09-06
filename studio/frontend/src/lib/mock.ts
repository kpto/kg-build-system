/**
 * The `?mock=1` fixture set: a realistic document plus the derived payloads the
 * backend would send, so every surface of the shell and every feature area is
 * developable without a running backend.
 *
 * Shapes follow API.md exactly; the document is the verbatim serialization of
 * `studio/backend/tests/test_document.py`'s fixture (see `sampleDocument.ts`).
 */

import type {
  AuthoringIndex,
  CatalogResponse,
  DataFile,
  ModuleEntry,
  OperatorEntry,
  Problem,
  StatusModel,
} from "./types";
import type { JsonObject, LogicalType, UnitName } from "./ir";
import { array, nullable, structRef, unit } from "./ir";
import { SAMPLE_DOCUMENT } from "./sampleDocument";

export { SAMPLE_DOCUMENT };

/** Kept in sync with `SAMPLE_DOCUMENT.project.package`. */
const SITES_PACKAGE = SAMPLE_DOCUMENT.project.package + ".table.sites";

export const MOCK_REVISION = SAMPLE_DOCUMENT.revision;

const str = unit("str");
const maybeStr = nullable(str);
const maybeFloat = nullable(unit("float"));
const maybeInt = nullable(unit("int"));

/**
 * The block palette, mirroring the operator table in `docs/AUTHORING_IR_CONTRACT.md`
 * with the `requires`/`produces` guards API.md describes.
 */
export const MOCK_OPERATORS: readonly OperatorEntry[] = [
  {
    operator: "where_present",
    label: "Keep rows where present",
    requires: { shape: "nullable" },
    produces: "non_null_unwrapped",
    arity: 1,
    group: "effect",
    docs: "Drops rows whose value is null and unwraps the nullable.",
  },
  {
    operator: "coalesce",
    label: "Default to a value",
    requires: { shape: "nullable" },
    produces: "non_null_unwrapped",
    arity: 2,
    group: "effect",
    docs: "Keeps every row, substituting the fallback for null.",
  },
  {
    operator: "keep_if",
    label: "Keep rows matching a predicate",
    requires: { shape: "any" },
    produces: "unchanged",
    arity: 2,
    group: "effect",
    docs: "The predicate must be a plain non-null bool.",
  },
  {
    operator: "expand",
    label: "Expand array into rows",
    requires: { shape: "array" },
    produces: "array_item",
    arity: 1,
    group: "navigation",
    docs: "One row per array item; the item's own nullability is preserved.",
  },
  {
    operator: "struct_field",
    label: "Pick a member",
    requires: { shape: "struct" },
    produces: "member",
    arity: 1,
    group: "navigation",
    docs: "parameters.name is the member; picking through a nullable struct yields nullable.",
  },
  {
    operator: "map_items",
    label: "Map items to a member",
    requires: { shape: "array_of_struct" },
    produces: "array_of_member",
    arity: 1,
    group: "navigation",
    docs: "Array[member]; item nullable if the element or the member is.",
  },
  {
    operator: "without_nulls",
    label: "Drop null items",
    requires: { shape: "array" },
    produces: "array_of_non_null",
    arity: 1,
    group: "navigation",
    docs: "Drops item nullability only.",
  },
  {
    operator: "sorted",
    label: "Sort items",
    requires: { shape: "array" },
    produces: "unchanged",
    arity: 1,
    group: "calculation",
  },
  { operator: "distinct", label: "Distinct items", requires: { shape: "array" }, produces: "unchanged", arity: 1, group: "calculation" },
  {
    operator: "join",
    label: "Join into text",
    requires: { shape: "array_of_non_null_str" },
    produces: "unit:str",
    arity: 2,
    group: "calculation",
    docs: "Items must be non-null str; the separator is a literal.",
  },
  { operator: "add", label: "Add", requires: { shape: "unit:float" }, produces: "unchanged", arity: 2, group: "calculation" },
  { operator: "subtract", label: "Subtract", requires: { shape: "unit:int" }, produces: "unchanged", arity: 2, group: "calculation" },
  { operator: "text", label: "As text", requires: { shape: "unit:int" }, produces: "unit:str", arity: 1, group: "calculation" },
  { operator: "concat", label: "Concatenate", requires: { shape: "unit:str" }, produces: "unit:str", arity: 2, group: "calculation" },
  { operator: "split_after", label: "Split after", requires: { shape: "unit:str" }, produces: "unit:str", arity: 2, group: "calculation" },
  { operator: "split_before", label: "Split before", requires: { shape: "unit:str" }, produces: "unit:str", arity: 2, group: "calculation" },
  { operator: "replaced", label: "Replace", requires: { shape: "unit:str" }, produces: "unit:str", arity: 3, group: "calculation" },
  { operator: "equals", label: "Equals", requires: { shape: "unit:str" }, produces: "unit:bool", arity: 2, group: "calculation" },
  { operator: "not", label: "Not", requires: { shape: "unit:bool" }, produces: "unit:bool", arity: 1, group: "calculation" },
  { operator: "and", label: "And", requires: { shape: "unit:bool" }, produces: "unit:bool", arity: 2, group: "calculation" },
  { operator: "or", label: "Or", requires: { shape: "unit:bool" }, produces: "unit:bool", arity: 2, group: "calculation" },
];

export const MOCK_INDEX: AuthoringIndex = {
  selectable: [
    {
      kind: "table",
      id: "sites",
      name: "sites",
      declaration_name: "SitesTable",
      group: null,
      paths: [
        { path: ["site_id"], logical_type: maybeStr, nullable: true, description: null },
        { path: ["site_name"], logical_type: maybeStr, nullable: true, description: null },
        {
          path: ["premises"],
          logical_type: nullable(structRef(SITES_PACKAGE, "PremisesStruct")),
          nullable: true,
        },
        {
          path: ["premises", "contact_name"],
          logical_type: maybeStr,
          nullable: true,
          description: null,
        },
        {
          path: ["premises", "contact"],
          logical_type: nullable(structRef(SITES_PACKAGE, "PremisesContactStruct")),
          nullable: true,
        },
        {
          path: ["premises", "contact", "email"],
          logical_type: maybeStr,
          nullable: true,
        },
        {
          path: ["premises", "contact", "location"],
          logical_type: nullable(structRef(SITES_PACKAGE, "PremisesContactLocationStruct")),
          nullable: true,
        },
        {
          path: ["premises", "contact", "location", "city"],
          logical_type: maybeStr,
          nullable: true,
        },
        {
          path: ["premises", "contact", "location", "room"],
          logical_type: maybeStr,
          nullable: true,
        },
        {
          path: ["priority_scores"],
          logical_type: array(maybeInt),
          nullable: true,
        },
      ],
    },
    {
      kind: "table",
      id: "equipment",
      name: "equipment",
      declaration_name: "EquipmentTable",
      group: null,
      paths: [
        { path: ["unit_ref"], logical_type: maybeStr, nullable: true },
        { path: ["site_id"], logical_type: maybeStr, nullable: true },
        { path: ["in_service"], logical_type: nullable(unit("bool")), nullable: true },
        { path: ["survey_period"], logical_type: maybeStr, nullable: true },
      ],
    },
    {
      kind: "table",
      id: "temperature_readings",
      name: "temperature",
      declaration_name: "TemperatureTable",
      group: "readings",
      paths: [
        { path: ["unit_ref"], logical_type: maybeStr, nullable: true },
        { path: ["deg_c"], logical_type: maybeFloat, nullable: true },
      ],
    },
    {
      kind: "projection",
      id: "site_cities",
      name: "site_cities",
      declaration_name: "SiteCityProjection",
      group: null,
      paths: [
        { path: ["site_id"], logical_type: maybeStr, nullable: true },
        { path: ["score"], logical_type: array(maybeInt), nullable: true },
      ],
    },
  ],
  components: [
    {
      id: "documented",
      kind: "node",
      tier: "category",
      resolved_properties: [{ name: "summary", logical_type: str, optional: false, declared_by: "documented" }],
      endpoint_is_category: { source: false, target: false },
    },
    {
      id: "site",
      kind: "node",
      tier: "concrete",
      resolved_properties: [
        { name: "summary", logical_type: str, optional: false, declared_by: "documented" },
        { name: "name", logical_type: str, optional: false, declared_by: "site" },
        { name: "city", logical_type: str, optional: false, declared_by: "site" },
      ],
      endpoint_is_category: { source: false, target: false },
    },
    {
      id: "unit",
      kind: "node",
      tier: "concrete",
      resolved_properties: [
        { name: "summary", logical_type: str, optional: false, declared_by: "documented" },
        { name: "name", logical_type: str, optional: false, declared_by: "unit" },
        { name: "in_service", logical_type: unit("bool"), optional: false, declared_by: "unit" },
      ],
      endpoint_is_category: { source: false, target: false },
    },
    {
      id: "has_unit",
      kind: "edge",
      tier: "concrete",
      resolved_properties: [{ name: "summary", logical_type: str, optional: false, declared_by: "documented" }],
      endpoint_is_category: { source: false, target: false },
    },
  ],
  structs: [
    {
      id: "premises",
      declaration_name: "PremisesStruct",
      name: "premises",
      module: SITES_PACKAGE,
      fields: [
        { name: "contact_name", logical_type: maybeStr },
        { name: "contact", logical_type: nullable(structRef(SITES_PACKAGE, "PremisesContactStruct")) },
      ],
    },
    {
      id: "premises_contact",
      declaration_name: "PremisesContactStruct",
      name: "premises_contact",
      module: SITES_PACKAGE,
      fields: [
        { name: "email", logical_type: maybeStr },
        {
          name: "location",
          logical_type: nullable(structRef(SITES_PACKAGE, "PremisesContactLocationStruct")),
        },
      ],
    },
  ],
  operators: MOCK_OPERATORS,
};

/* ------------------------------------------------------------------------- problems */

export const MOCK_PROBLEMS: readonly Problem[] = [
  {
    id: "a1f3c9",
    tier: "types",
    severity: "error",
    message:
      "SiteNode.city expects UnitType(name='str'), but the expression resolves to UnitType(name='int')",
    code: "reportArgumentType",
    file: "kg_project/bindings/site/__init__.py",
    line: 24,
    column: 18,
    end_line: 24,
    end_column: 41,
    ref: "binding:site_binding.property.city",
    ref_trusted: "anchor",
    hint: "Property 'city' is declared str on component SiteNode.",
  },
  {
    id: "b7d201",
    tier: "types",
    severity: "warning",
    message: "PremisesStruct.contact is never read by any binding",
    code: "reportUnusedVariable",
    file: "kg_project/table/sites/__init__.py",
    line: 61,
    column: 5,
    end_line: 61,
    end_column: 30,
    ref: "struct:premises.property.contact",
    ref_trusted: "name",
    hint: null,
  },
  {
    id: "c24e88",
    tier: "blueprint",
    severity: "error",
    message: "edge component 'has_unit' binds a destination that is not a node component",
    code: "EndpointDescentError",
    file: "kg_project/topology/has_unit/site__unit.py",
    line: 12,
    column: 1,
    end_line: 18,
    end_column: 0,
    ref: "component:has_unit",
    ref_trusted: "name",
    hint: "Check the declared target of the edge component.",
  },
  {
    id: "d90f13",
    tier: "blueprint",
    severity: "error",
    message: "table 'equipment' has no source bound",
    code: "MissingSourceError",
    file: "kg_project/sources.py",
    line: 9,
    column: 1,
    ref: null,
    ref_trusted: null,
    hint: "Add a source for the table in the Sources tab.",
  },
  {
    id: "e55a02",
    tier: "build",
    severity: "warning",
    message: "step core::aggregate.node.site materialized 0 rows",
    code: "EmptyStep",
    file: null,
    line: null,
    column: null,
    ref: "component:site",
    ref_trusted: "name",
    hint: null,
  },
  {
    id: "f01b64",
    tier: "document",
    severity: "info",
    message: "concrete component 'unit' mixes in a template no other component uses",
    code: "UnusedMixin",
    file: "project.ir.json",
    line: null,
    column: null,
    ref: "component:unit",
    ref_trusted: "anchor",
    hint: "Templates are shared by intent, not by requirement.",
  },
];

/* -------------------------------------------------------------------- catalog/status */

const module = (
  id: string,
  role: string,
  summary: string,
  configuration: JsonObject | null,
): ModuleEntry => ({
  id,
  role,
  label: id
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" "),
  summary,
  import_module: "kg_build_system.modules",
  class_qualname: `${id.replace(/(^|_)(\w)/g, (_all, _sep, ch: string) => ch.toUpperCase())}Module`,
  configuration_schema: null,
  default_configuration: configuration,
});

export const MOCK_CATALOG: CatalogResponse = {
  modules: [
    module("collapse_exact_duplicates", "operator", "Drop rows identical to one already seen.", null),
    module("merge_compatible_facts", "operator", "Merge facts that agree on their build key.", null),
    module(
      "reject_conflicting_non_null_values",
      "operator",
      "Fail the build when two non-null values disagree.",
      null,
    ),
    module("file", "target", "Write the graph to a file under the project.", { relative_path: "graph.jsonl" }),
    module("meta_graph", "target", "Emit the studio meta-graph page alongside the build.", null),
    module("neo4j", "target", "Load the graph into a Neo4j instance.", { database: "neo4j" }),
  ],
  units: (
    [
      "bool",
      "int",
      "float",
      "str",
      "date",
      "time",
      "timestamp",
      "uuid",
    ] as UnitName[]
  ).map((name) => ({
    name,
    representative: ["date", "time", "timestamp", "uuid"].includes(name)
      ? name.charAt(0).toUpperCase() + name.slice(1)
      : name,
    graph_safe: true,
  })),
  operators: MOCK_OPERATORS,
  vocabulary: {},
};

export const MOCK_STATUS: StatusModel = {
  revision: MOCK_REVISION,
  generation: { state: "dirty", at: "2026-09-06T09:12:04Z", changed: ["kg_project/bindings/site/__init__.py"], error: null },
  blueprint: { ok: false, errors: 1 },
  types: { errors: 1, warnings: 1, state: "ready" },
  build: { state: "never" },
  project_root: "/abs/path/studio_test_project",
};

export const MOCK_DATA_FILES: readonly DataFile[] = [
  { location: "data/sites.json", name: "sites", format: "json", size_bytes: "18412" },
  { location: "data/equipment.json", name: "equipment", format: "json", size_bytes: "9310" },
  { location: "data/readings/temperature.json", name: "temperature", format: "json", size_bytes: "40211" },
  { location: "data/readings/mechanical/vibration.json", name: "vibration", format: "json", size_bytes: "7788" },
];

/** The type vocabulary the mock `TypePicker` offers, matching the catalogue. */
export const MOCK_UNIT_NAMES: readonly UnitName[] = [
  "bool",
  "int",
  "float",
  "str",
  "date",
  "time",
  "timestamp",
  "uuid",
];

export const MOCK_STRUCT_OPTIONS: readonly { module: string; qualname: string; label: string }[] = (
  SAMPLE_DOCUMENT.structs ?? []
).map((struct) => ({
  module: `${SITES_PACKAGE}`,
  qualname: struct.declaration_name,
  label: struct.name,
}));

export type { LogicalType };
