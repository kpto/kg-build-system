import type { CampaignView } from "@/shared/model/campaign";
import type { InspectorSelection } from "@/shared/types/selection";
import type { EntityKind, IndexedBinding, LineageGraph, WorkflowStep } from "@/lib/types";
import { expressionPreview, expressionTree } from "@/lib/expressions";
import { stepKey } from "@/lib/indexes";
import type {
  PropertiesAnnotation,
  PropertiesBlock,
  PropertiesField,
  PropertiesModel,
  PropertiesRail,
  PropertiesRailId,
  PropertiesRow,
  PropertiesSection,
} from "./PropertiesModel";

const RAILS: PropertiesRail[] = [
  { id: "definition", label: "Definition", question: "What is this?", icon: "info" },
  { id: "production", label: "Production", question: "How is it produced?", icon: "trace" },
  { id: "emission", label: "Emission", question: "What does it emit?", icon: "code" },
  { id: "dependencies", label: "Dependencies", question: "What depends on it?", icon: "branch" },
  { id: "context", label: "Context", question: "What else is recorded?", icon: "layers" },
];

/** Each rail is a question; a section belongs to the rails it answers. */
const RAIL_TARGETS: Record<PropertiesRailId, string[]> = {
  definition: [
    "identity",
    "definition",
    "binding",
    "property",
    "entity",
    "asset",
    "data entity",
    "field",
    "lineage node",
    "properties",
    "artifacts",
    "payload",
    "description",
  ],
  production: [
    "branches",
    "expression",
    "property expressions",
    "rows",
    "layout",
    "source",
  ],
  emission: ["sql preview", "sql"],
  dependencies: ["connections", "provenance", "impact", "endpoints"],
  context: ["annotations"],
};

const SECTION_QUESTIONS: Record<string, string> = {
  identity: "What identifies this subject?",
  artifacts: "Which artifacts does this step declare?",
  payload: "What instruction payload does this step carry?",
  connections: "What does this step consume and produce?",
  binding: "What identifies this binding?",
  rows: "Which row source does this binding use?",
  "property expressions": "Which expressions define these properties?",
  definition: "What defines this property?",
  branches: "Which binding branches produce this value?",
  "sql preview": "What SQL does this branch emit?",
  provenance: "Which steps consume this value?",
  entity: "What is this entity?",
  properties: "Which properties define this entity?",
  endpoints: "Which entities does this edge connect?",
  "data entity": "What is this data entity?",
  fields: "Which fields does this entity declare?",
  asset: "What semantics does this asset declare?",
  layout: "How is this asset laid out?",
  field: "What identifies this field?",
  description: "What does this field mean?",
  expression: "Which expression defines this value?",
  "lineage node": "What does this lineage node represent?",
  annotations: "Which annotations apply to this subject?",
  source: "Where is this value declared?",
  "payload / published value": "What value is published here?",
};

const KIND_LABEL: Record<InspectorSelection["kind"], string> = {
  step: "step",
  binding: "binding",
  property: "property",
  topology: "entity",
  data: "data",
  asset: "asset",
  field: "field",
  "lineage-node": "lineage",
};

const PROSE_FIELDS = new Set(["coverage", "authority"]);

function field(
  label: string,
  value: string | number | null | undefined,
  title?: string,
): PropertiesField {
  const text = value === undefined || value === null || value === "" ? "—" : String(value);
  return {
    id: `field:${label}`,
    label,
    value: text,
    title,
    copy: true,
    mono: !PROSE_FIELDS.has(label),
  };
}

function code(label: string, text: string): PropertiesBlock {
  return { kind: "code", label, text };
}

function json(label: string, value: unknown): PropertiesBlock {
  return code(label, JSON.stringify(value ?? {}, null, 2));
}

function pills(values: string[], empty?: string): PropertiesBlock {
  return { kind: "pills", values, empty };
}

function text(
  value: string,
  options: { mono?: boolean; breakAll?: boolean } = {},
): PropertiesBlock {
  return { kind: "text", text: value, ...options };
}

function empty(value: string): PropertiesBlock {
  return { kind: "empty", text: value };
}

function annotation(
  annotations: PropertiesAnnotation["annotations"] | undefined,
  context: PropertiesAnnotation["context"],
): PropertiesAnnotation {
  return { annotations: annotations ?? [], context };
}

function section(
  title: string,
  blocks: PropertiesBlock[],
  options: {
    id?: string;
    question?: string;
    count?: string;
    annotations?: PropertiesAnnotation;
  } = {},
): PropertiesSection {
  const id = options.id ?? title.toLowerCase();
  return {
    id,
    title,
    question:
      options.question ??
      SECTION_QUESTIONS[id] ??
      `What does ${id} show?`,
    count: options.count,
    blocks,
    annotations: options.annotations,
  };
}

function row(value: PropertiesRow): PropertiesBlock {
  return { kind: "row", row: value };
}

function stepSections(campaign: CampaignView, step: WorkflowStep): PropertiesSection[] {
  const index = campaign.record.index;
  const key = stepKey(step.id);
  const incoming = index.incomingByStepId.get(key) ?? [];
  const outgoing = index.outgoingByStepId.get(key) ?? [];
  const artifacts = [
    ...(step.outputs ?? []).map((output) => output.type.join(".")),
    ...(step.inputs ?? []).map((input) => input.type.join(".")),
  ];

  const connectionRow = (
    direction: "in" | "out",
    id: string,
    label: string,
    opening: string,
  ): PropertiesBlock =>
    row({
      id: `${direction}-${id}`,
      kind: "connection",
      label,
      meta: opening,
      direction,
    });

  return [
    section("Identity", [
      { kind: "field", field: field("component", step.id[0]) },
      { kind: "field", field: field("step", step.id[1]) },
      { kind: "field", field: field("emitter", step.instruction.kind.join(":")) },
      { kind: "field", field: field("assembly", step.assembly_preference ?? "—") },
    ]),
    section("Artifacts", [
      artifacts.length ? pills(artifacts) : empty("No declared artifacts."),
    ]),
    section("Payload", [json("JSON", step.instruction.payload)]),
    section(
      "Connections",
      [
        ...incoming.map((connection) =>
          connectionRow(
            "in",
            connection.id,
            connection.outputStepId.join("/"),
            connection.input.openingName,
          ),
        ),
        ...outgoing.map((connection) =>
          connectionRow(
            "out",
            connection.id,
            connection.inputStepId.join("/"),
            connection.input.openingName,
          ),
        ),
        !incoming.length && !outgoing.length ? empty("No connections.") : null,
      ].filter((block): block is PropertiesBlock => Boolean(block)),
      { count: `${incoming.length} in / ${outgoing.length} out` },
    ),
  ];
}

function bindingSections(campaign: CampaignView, binding: IndexedBinding): PropertiesSection[] {
  const expressions = Object.entries(binding.binding.properties ?? {});
  const annotationRef = annotation(binding.binding.annotations, {
    kind: binding.kind,
    component: binding.component,
  });

  return [
    section(
      "Binding",
      [
        { kind: "field", field: field("component", binding.component) },
        { kind: "field", field: field("kind", binding.kind) },
        { kind: "field", field: field("index", binding.index) },
        { kind: "field", field: field("artifact", binding.outputArtifact.join(".")) },
        { kind: "field", field: field("step", binding.step?.id.join("/") ?? "—") },
      ],
      { annotations: annotationRef },
    ),
    section("Rows", [json("JSON", binding.binding.rows ?? {})]),
    section(
      "Property expressions",
      expressions.length
        ? expressions.map(([property, expression]) =>
            row({
              id: `expression:${property}`,
              kind: "branch",
              label: property,
              blocks: [
                code(
                  "Expression",
                  expressionTree(expression).join("\n") || expressionPreview(expression),
                ),
              ],
            }),
          )
        : [empty("No property expressions.")],
      { count: String(expressions.length) },
    ),
  ];
}

function propertySections(
  campaign: CampaignView,
  selection: Extract<InspectorSelection, { kind: "property" }>,
): PropertiesSection[] {
  const index = campaign.record.index;
  const lineage: LineageGraph = selection.lineage;
  const property = (
    selection.selection.kind === "node"
      ? index.topologyNodesByName.get(selection.selection.component)
      : index.topologyEdgesByName.get(selection.selection.component)
  )?.properties?.find((candidate) => candidate.name === selection.selection.property);
  const branch = lineage.branches[0];
  const annotationRef = annotation(property?.annotations, {
    kind: selection.selection.kind,
    component: selection.selection.component,
    property: selection.selection.property,
  });

  return [
    section(
      "Definition",
      [
        { kind: "field", field: field("entity", selection.selection.kind) },
        { kind: "field", field: field("ref", property?.ref?.join(".") ?? "—") },
        {
          kind: "field",
          field: field(
            "type",
            property?.logical_type?.name ?? property?.logical_type?.kind ?? "—",
          ),
        },
        ...(property?.description
          ? [text(property.description)]
          : []),
      ],
      { annotations: annotationRef },
    ),
    section(
      "Branches",
      lineage.branches.length
        ? lineage.branches.map((branchItem) =>
            row({
              id: `branch:${branchItem.key}`,
              kind: "branch",
              label: `binding ${branchItem.binding.index}`,
              meta: branchItem.binding.kind,
              blocks: [
                {
                  kind: "field",
                  field: field(
                    "fields",
                    branchItem.fieldKeys.length
                      ? branchItem.fieldKeys.join(", ")
                      : "literal expression",
                  ),
                },
                {
                  kind: "field",
                  field: field(
                    "source",
                    branchItem.sourceRelations.length
                      ? `${branchItem.assetNames.join(", ")} → ${branchItem.sourceRelations.join(", ")}`
                      : "no source relation",
                  ),
                },
                code("Expression", expressionTree(branchItem.expression).join("\n") || "—"),
              ],
            }),
          )
        : [empty("No binding branches.")],
      { count: String(lineage.branches.length) },
    ),
    section("SQL preview", [
      code(
        "SQL",
        branch?.bindingStep?.instruction.payload?.sql?.toString() ??
          "No SQL for this branch.",
      ),
    ]),
    section("Provenance", [
      ...lineage.branches.flatMap((branchItem) =>
        branchItem.targetSteps.map((step) =>
          row({
            id: `target:${branchItem.key}:${stepKey(step.id)}`,
            kind: "target",
            label: step.id.join("/"),
          }),
        ),
      ),
      lineage.branches.some((branchItem) => branchItem.targetSteps.length)
        ? null
        : empty("No target steps recorded."),
    ].filter((block): block is PropertiesBlock => Boolean(block))),
  ];
}

function topologySections(
  campaign: CampaignView,
  entityKind: EntityKind,
  name: string,
): PropertiesSection[] {
  const index = campaign.record.index;
  const entity =
    entityKind === "node"
      ? index.topologyNodesByName.get(name)
      : index.topologyEdgesByName.get(name);
  const properties = entity?.properties ?? [];
  const annotationRef = annotation(entity?.annotations, {
    kind: entityKind,
    component: name,
  });
  const pillsValues = [
    ...(entity?.labels ?? []),
    ...(entity?.abstract ? ["abstract"] : []),
  ];

  const blocks: PropertiesBlock[] = [
    text(entity?.description ?? "No description."),
  ];
  if (pillsValues.length) blocks.push(pills(pillsValues));

  const sections: PropertiesSection[] = [
    section("Entity", blocks, { annotations: annotationRef }),
    section(
      "Properties",
      properties.length
        ? properties.map((property) =>
            row({
              id: `property:${property.name}`,
              kind: "property",
              label: property.name,
              meta:
                property.logical_type?.name ?? property.logical_type?.kind,
              title: `Trace ${name}.${property.name} to lineage`,
              actions: [
                {
                  id: "select-property",
                  label: property.name,
                  icon: "trace",
                  title: `Trace ${name}.${property.name} to lineage`,
                  run: () =>
                    campaign.commands.selectProperty(
                      entityKind,
                      name,
                      property.name,
                    ),
                },
              ],
            }),
          )
        : [empty("No properties.")],
      { count: String(properties.length) },
    ),
  ];

  if (entityKind === "edge") {
    const edge = entity as { source?: string[]; target?: string[] } | undefined;
    sections.push(
      section("Endpoints", [
        { kind: "field", field: field("source", edge?.source?.join(".") ?? "—") },
        { kind: "field", field: field("target", edge?.target?.join(".") ?? "—") },
      ]),
    );
  }

  return sections;
}

function dataSections(
  campaign: CampaignView,
  entityType: "relation" | "projection" | "struct",
  name: string,
): PropertiesSection[] {
  const index = campaign.record.index;
  const entity =
    entityType === "relation"
      ? index.relationByName.get(name)
      : entityType === "projection"
        ? index.projectionByName.get(name)
        : index.structByName.get(name);
  const columns = entity?.columns ?? [];
  const blocks: PropertiesBlock[] = [
    text(entity?.description ?? "No description."),
  ];
  if (entityType === "projection" && "row_source" in (entity ?? {})) {
    blocks.push(json("JSON", (entity as { row_source?: unknown }).row_source));
  }

  return [
    section("Data entity", blocks),
    section(
      "Fields",
      columns.length
        ? columns.map((column) =>
            row({
              id: `column:${column.name}`,
              kind: "data-field",
              label: column.name,
              meta:
                column.logical_type?.name ?? column.logical_type?.kind,
              blocks: column.expression
                ? [
                    {
                      kind: "field",
                      field: field(
                        "expression",
                        expressionPreview(column.expression),
                        expressionPreview(column.expression),
                      ),
                    },
                  ]
                : undefined,
            }),
          )
        : [empty("No fields.")],
      { count: String(columns.length) },
    ),
  ];
}

function assetSections(campaign: CampaignView, name: string): PropertiesSection[] {
  const asset = campaign.record.index.assetsByName.get(name);
  return [
    section("Asset", [
      text(
        asset?.semantics?.subject ??
          asset?.semantics?.description ??
          "No semantics.",
      ),
      { kind: "field", field: field("coverage", asset?.semantics?.coverage ?? "—") },
      { kind: "field", field: field("authority", asset?.semantics?.authority ?? "—") },
      { kind: "field", field: field("version", asset?.version ?? "—") },
    ]),
    section("Layout", [json("JSON", asset?.layout ?? {})]),
  ];
}

function fieldSections(campaign: CampaignView, fieldKey: string): PropertiesSection[] {
  const fieldLocation = campaign.record.index.fieldsByKey.get(fieldKey);
  const sections: PropertiesSection[] = [
    section("Field", [
      { kind: "field", field: field("owner", fieldLocation?.ownerName ?? "—") },
      { kind: "field", field: field("kind", fieldLocation?.ownerKind ?? "—") },
      {
        kind: "field",
        field: field(
          "type",
          fieldLocation?.field.logical_type?.name ??
            fieldLocation?.field.logical_type?.kind ??
            "—",
        ),
      },
    ]),
  ];
  if (fieldLocation?.field.description) {
    sections.push(section("Description", [text(fieldLocation.field.description)]));
  }
  if (fieldLocation?.field.expression) {
    sections.push(
      section("Expression", [
        code("Expression", expressionTree(fieldLocation.field.expression).join("\n")),
      ]),
    );
  }
  return sections;
}

function lineageNodeSections(
  campaign: CampaignView,
  selection: Extract<InspectorSelection, { kind: "lineage-node" }>,
): PropertiesSection[] {
  const node = selection.node;
  const sections: PropertiesSection[] = [
    section("Lineage node", [
      { kind: "field", field: field("lane", node.lane) },
      { kind: "field", field: field("kind", node.kind) },
      { kind: "field", field: field("category", node.category) },
      ...(node.metadata.description ? [text(node.metadata.description)] : []),
    ]),
  ];

  if (node.metadata.expression) {
    sections.push(
      section("Expression", [
        code("Expression", expressionTree(node.metadata.expression).join("\n")),
      ]),
    );
  }
  if (node.metadata.artifacts.length) {
    sections.push(
      section("Artifacts", [
        pills(node.metadata.artifacts.map((artifact) => artifact.join("."))),
      ]),
    );
  }
  if (node.metadata.sqlPreview) {
    sections.push(section("SQL preview", [code("SQL", node.metadata.sqlPreview)]));
  }
  if (node.metadata.sourceLocation) {
    sections.push(
      section("Source", [
        text(node.metadata.sourceLocation, { mono: true, breakAll: true }),
      ]),
    );
  }
  if (node.metadata.payload) {
    sections.push(
      section("Payload / published value", [json("JSON", node.metadata.payload)]),
    );
  }

  sections.push(
    section(
      "Annotations",
      node.metadata.annotations.length
        ? []
        : [empty("No annotations.")],
      {
        count: String(node.metadata.annotations.length),
        annotations: annotation(node.metadata.annotations, {
          component: node.component,
          property: node.property,
        }),
      },
    ),
  );

  return sections;
}

/**
 * Build the Properties panel model.
 *
 * Evidence sections are computed here from the index, lineage and audit data.
 * The rail the reviewer is reading is view state; this builder exposes every
 * rail and the exact sections each one answers.
 */
export function buildPropertiesModel(campaign: CampaignView): PropertiesModel {
  const selection = campaign.selection;
  let sections: PropertiesSection[] = [];
  let subjectTitle: string | undefined;

  if (selection) {
    switch (selection.kind) {
      case "step":
        subjectTitle = selection.step.id[1];
        sections = stepSections(campaign, selection.step);
        break;
      case "binding":
        subjectTitle = `${selection.binding.component}[${selection.binding.index}]`;
        sections = bindingSections(campaign, selection.binding);
        break;
      case "property":
        subjectTitle = `${selection.selection.component}.${selection.selection.property}`;
        sections = propertySections(campaign, selection);
        break;
      case "topology":
        subjectTitle = selection.name;
        sections = topologySections(campaign, selection.entityKind, selection.name);
        break;
      case "data":
        subjectTitle = selection.name;
        sections = dataSections(campaign, selection.entityType, selection.name);
        break;
      case "asset":
        subjectTitle = selection.name;
        sections = assetSections(campaign, selection.name);
        break;
      case "field":
        subjectTitle = selection.fieldKey;
        sections = fieldSections(campaign, selection.fieldKey);
        break;
      case "lineage-node":
        subjectTitle = selection.node.label;
        sections = lineageNodeSections(campaign, selection);
        break;
    }
  }

  const sectionsFor = RAILS.reduce(
    (result, rail) => {
      const matched = sections.filter((entry) =>
        RAIL_TARGETS[rail.id].some((target) => entry.id.includes(target)),
      );
      result[rail.id] = matched.length
        ? matched
        : [
            section(
              rail.label,
              [empty(`No ${rail.label.toLowerCase()} evidence recorded for this subject.`)],
              { id: rail.id, question: rail.question },
            ),
          ];
      return result;
    },
    {} as Record<PropertiesRailId, PropertiesSection[]>,
  );

  return {
    id: "properties",
    title: "Properties",
    icon: "properties",
    empty: !selection,
    kind: selection?.kind,
    kindLabel: selection ? KIND_LABEL[selection.kind] : undefined,
    subjectTitle,
    emptyState: selection
      ? undefined
      : {
          title: "Nothing selected",
          hint: "Choose a property, workflow step or entity in the Outliner to read its evidence here.",
          actionLabel: "Search subjects",
        },
    rails: RAILS,
    sectionsFor,
    metaGraph: campaign.record.index.metaGraph,
  };
}
