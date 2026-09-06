/**
 * Document edits for the contracts feature. Every function is a `(draft) => draft`
 * rebuilder handed straight to `apply(...)`; the models are frozen, so an edit is
 * always a rebuild of the part that changed. `logic.ts` answers *what is legal*, this
 * file performs the change once it is legal.
 */

import {
  array,
  nullable,
  sectionItems,
  structRef,
  unit,
  type DataField,
  type ProjectDocument,
  type Projection,
  type Struct,
  type Table,
} from "@/lib/ir";
import type { NullabilityTrust } from "@/lib/ir";
import { pascalCase, snakeCase, suggestDeclarationName, suggestId } from "./logic";

type FieldSection = "tables" | "structs";

const strType = nullable(unit("str"));

/** The default a freshly added field carries until the author sets one. */
export const DEFAULT_FIELD_TYPE = strType;

function mapEntity(
  document: ProjectDocument,
  section: FieldSection,
  id: string,
  changes: Partial<Table & Struct>,
): ProjectDocument {
  const items = sectionItems(document, section);
  return {
    ...document,
    [section]: items.map((item) => (item.id === id ? ({ ...item, ...changes } as Table & Struct) : item)),
  } as ProjectDocument;
}

export function setFields(
  document: ProjectDocument,
  section: FieldSection,
  id: string,
  fields: readonly DataField[],
): ProjectDocument {
  return mapEntity(document, section, id, { fields });
}

export function updateField(
  document: ProjectDocument,
  section: FieldSection,
  id: string,
  fieldName: string,
  changes: Partial<DataField>,
): ProjectDocument {
  const items = sectionItems(document, section);
  return {
    ...document,
    [section]: items.map((item) =>
      item.id !== id
        ? item
        : {
            ...item,
            fields: (item.fields ?? []).map((field) =>
              field.name === fieldName ? ({ ...field, ...changes } as DataField) : field,
            ),
          },
    ),
  } as ProjectDocument;
}

/**
 * Rename a field, keeping the rename collision-safe (a duplicate name within the
 * entity is refused by returning the document unchanged). `logic.suggestId` never
 * collides, so the caller can pass a suggested name and trust it.
 */
export function renameField(
  document: ProjectDocument,
  section: FieldSection,
  id: string,
  oldName: string,
  newName: string,
): ProjectDocument {
  if (!newName || oldName === newName) return document;
  const item = sectionItems(document, section).find((entity) => entity.id === id);
  if (!item) return document;
  const fields = (item.fields ?? []) as DataField[];
  if (fields.some((field) => field.name === newName)) return document;
  return setFields(
    document,
    section,
    id,
    fields.map((field) => (field.name === oldName ? { ...field, name: newName } : field)),
  );
}

export function deleteField(
  document: ProjectDocument,
  section: FieldSection,
  id: string,
  fieldName: string,
): ProjectDocument {
  const item = sectionItems(document, section).find((entity) => entity.id === id);
  if (!item) return document;
  return setFields(
    document,
    section,
    id,
    ((item.fields ?? []) as DataField[]).filter((field) => field.name !== fieldName),
  );
}

/** Append a field with a fresh, entity-unique name; returns the name it chose. */
export function makeField(label: string, takenNames: Iterable<string>): DataField {
  const name = suggestId(label || "field", takenNames);
  return {
    name,
    logical_type: DEFAULT_FIELD_TYPE,
    description: null,
    nullability: "defaulted" as NullabilityTrust,
    schema_path: "",
    annotations: [],
  };
}

export function addField(
  document: ProjectDocument,
  section: FieldSection,
  id: string,
  field: DataField,
): ProjectDocument {
  const item = sectionItems(document, section).find((entity) => entity.id === id);
  if (!item) return document;
  return setFields(document, section, id, [...((item.fields ?? []) as DataField[]), field]);
}

export function makeStruct(label: string, document: ProjectDocument): { struct: Struct; document: ProjectDocument } {
  const id = suggestId(label || "record", sectionItems(document, "structs").map((item) => item.id));
  const struct: Struct = {
    id,
    declaration_name: suggestDeclarationName("struct", id),
    name: id,
    description: null,
    fields: [],
    annotations: [],
  };
  return { struct, document: { ...document, structs: [...sectionItems(document, "structs"), struct] } };
}

/** The `(module, qualname)` a field type gets when it points at a struct by id. */
export function structFieldType(struct: Struct): ReturnType<typeof nullable> {
  return nullable(structRef("", struct.declaration_name));
}

export function makeArrayNullableInt(): ReturnType<typeof nullable> {
  return nullable(array(nullable(unit("int"))));
}

/** Create a table (or a group when `group`) with a document-unique id. */
export function makeTable(label: string, document: ProjectDocument, group = false): { table: Table; document: ProjectDocument } {
  const id = suggestId(label, sectionItems(document, "tables").map((item) => item.id));
  const name = snakeCase(label) || id;
  const table: Table = {
    id,
    declaration_name: suggestDeclarationName("table", id, group),
    name,
    description: null,
    fields: [],
    members: group ? [] : [],
    annotations: [],
    group: null,
  };
  return { table, document: { ...document, tables: [...sectionItems(document, "tables"), table] } };
}

export function deleteEntity(
  document: ProjectDocument,
  section: FieldSection | "projections",
  id: string,
): ProjectDocument {
  const items = sectionItems(document, section).filter((item) => item.id !== id);
  return { ...document, [section]: items } as ProjectDocument;
}

/* ------------------------------------------------------------------ projections */

export function makeProjection(label: string, document: ProjectDocument): { projection: Projection; document: ProjectDocument } {
  const id = suggestId(label, sectionItems(document, "projections").map((item) => item.id));
  const projection: Projection = {
    id,
    declaration_name: suggestDeclarationName("projection", id),
    name: id,
    description: null,
    fields: [],
    annotations: [],
  };
  return { projection, document: { ...document, projections: [...sectionItems(document, "projections"), projection] } };
}

/** Set a projection's description; outputs are edited through `updateProjectionField`. */
export function patchProjection(document: ProjectDocument, id: string, changes: Partial<Projection>): ProjectDocument {
  return {
    ...document,
    projections: sectionItems(document, "projections").map((item) =>
      item.id === id ? ({ ...item, ...changes } as Projection) : item,
    ),
  };
}

/**
 * Rename a declaration (table/struct/projection). The logical name is what every
 * field reference stores, so the caller must only rename when nothing dangles; the
 * suggestion is built from the class name so `Sites Table` → name `sites`.
 */
export function renameEntity(
  document: ProjectDocument,
  section: FieldSection | "projections",
  id: string,
  name: string,
): ProjectDocument {
  const snake = snakeCase(name) || id;
  const isTable = section === "tables";
  const items = sectionItems(document, section);
  return {
    ...document,
    [section]: items.map((item) =>
      item.id === id
        ? {
            ...item,
            name: snake,
            declaration_name: isTable
              ? suggestDeclarationName("table", snake, (item as Table).members?.length ? true : false)
              : section === "structs"
                ? suggestDeclarationName("struct", snake)
                : suggestDeclarationName("projection", snake),
          }
        : item,
    ),
  } as ProjectDocument;
}

/** The Pascal head of a name, used to preview a class name while typing. */
export const classHead = (label: string): string => pascalCase(snakeCase(label));
