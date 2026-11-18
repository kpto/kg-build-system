/**
 * The model of one virtual collection.
 *
 * A collection is a layer read as a group, not a declared subject. Its
 * dependency is the full layer DAG below it at layer resolution; its dependant
 * is only the immediate layer above it. Items are the members of the layer, and
 * coverage counts what the layer carries. No aggregate purpose or claim is
 * invented.
 */

import type { ConceptKind } from "@/lib/concepts";
import type { PurposeLevelKind } from "@/shared/design/meaning";
import { relationNamesFromRowSource, resolveAssetName } from "@/lib/indexes";
import type { IndexedBinding, ViewerIndex } from "@/lib/types";
import {
  COLLECTIONS,
  collectionTitle,
  type CollectionId,
} from "@/workbench/collections";
import {
  buildWorkflowModel,
  groupWorkflowRows,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import {
  EMPTY_MEANING,
  constitutionModel,
  contributionModel,
  stepBoundaryModel,
  type ConstitutionBinding,
  type ConstitutionFrameId,
  type ConstitutionModel,
  type ConstitutionNode,
  type ConstitutionRelation,
  type ConstitutionSubjectLike,
} from "./constitution";

export type CollectionAxisKind = "data" | "graph" | "workflow";

export interface CollectionRef {
  id: CollectionId;
  component?: string;
}

export interface CollectionLayer {
  key: string;
  title: string;
  concept: ConceptKind;
  count: number;
  axis: CollectionAxisKind;
  note?: string;
  collection?: CollectionRef;
  current?: boolean;
}

export interface CollectionAxis {
  axis: CollectionAxisKind;
  label: string;
  layers: CollectionLayer[];
}

export interface CollectionItem {
  key: string;
  concept: ConceptKind;
  name: string;
  component?: string;
  property?: string;
  ownerConcept?: ConceptKind;
  bindingIndex?: number;
  stepId?: [string, string];
  cells: string[];
  /** A workflow component opens its own collection instead of a participant. */
  collection?: CollectionRef;
}

export interface CollectionItems {
  columns: string[];
  template: string;
  rows: CollectionItem[];
  empty: string;
}

export interface CollectionCoverageRow {
  key: string;
  measure: string;
  count: number;
  reading: string;
}

export interface CollectionModel {
  id: CollectionId;
  component?: string;
  concept: ConceptKind;
  kicker: string;
  title: string;
  subtitle: string;
  facts: Array<{ label: string; value: string }>;
  dependency: { axes: CollectionAxis[]; empty: string };
  dependants: { axes: CollectionAxis[]; empty: string };
  items: CollectionItems;
  coverage: CollectionCoverageRow[];
}

type MeaningLike =
  | { purpose?: unknown; claims?: unknown[]; limitations?: unknown[]; frames?: unknown[] }
  | undefined;

function hasMeaning(meaning: MeaningLike): boolean {
  return Boolean(
    meaning &&
      (meaning.purpose ||
        meaning.claims?.length ||
        meaning.limitations?.length ||
        meaning.frames?.length),
  );
}

function scans(binding: IndexedBinding, name: string): boolean {
  return relationNamesFromRowSource(binding.binding.rows).includes(name);
}

function directBindings(index: ViewerIndex, name: string): IndexedBinding[] {
  return index.bindings.filter((binding) => scans(binding, name));
}

function directDerived(
  index: ViewerIndex,
  name: string,
): ViewerIndex["projections"] {
  return index.projections.filter((projection) =>
    relationNamesFromRowSource(projection.row_source).includes(name),
  );
}

function bindingName(binding: IndexedBinding): string {
  return (
    binding.binding.name ??
    binding.binding.debug_name ??
    `binding #${binding.index}`
  );
}

function bindingMeaning(binding: IndexedBinding): MeaningLike {
  return binding.binding.meaning ?? binding.binding.semantics;
}

function assetRelations(index: ViewerIndex, name: string): number {
  return index.relations.filter(
    (relation) => resolveAssetName(index, relation.name) === name,
  ).length;
}

function componentBindings(
  index: ViewerIndex,
  kind: "node" | "edge",
  name: string,
): IndexedBinding[] {
  return index.bindings.filter(
    (binding) => binding.kind === kind && binding.component === name,
  );
}

function immediateChildren(
  index: ViewerIndex,
  abstract: string,
): Array<{ name: string; kind: "node" | "edge"; abstract: boolean }> {
  const children: Array<{
    name: string;
    kind: "node" | "edge";
    abstract: boolean;
  }> = [];
  for (const node of index.topologyNodes) {
    if (node.parent?.[2] !== abstract) continue;
    children.push({
      name: node.name,
      kind: "node",
      abstract: Boolean(node.abstract),
    });
  }
  for (const edge of index.topologyEdges) {
    if (edge.parent?.[2] !== abstract) continue;
    children.push({
      name: edge.name,
      kind: "edge",
      abstract: Boolean(edge.abstract),
    });
  }
  return children;
}

function layer(
  axis: CollectionAxisKind,
  key: string,
  title: string,
  concept: ConceptKind,
  count: number,
  options: {
    note?: string;
    collection?: CollectionRef;
    current?: boolean;
  } = {},
): CollectionLayer {
  return {
    key: `${axis}:${key}`,
    title,
    concept,
    count,
    axis,
    ...options,
  };
}

function axis(
  kind: CollectionAxisKind,
  layers: CollectionLayer[],
): CollectionAxis | undefined {
  if (!layers.length) return undefined;
  const label =
    kind === "data"
      ? "Data dependency"
      : kind === "graph"
        ? "Graph dependency"
        : "Workflow dependency";
  return {
    axis: kind,
    label,
    layers: layers.map((entry) => ({ ...entry, axis: kind })),
  };
}

function dependantAxis(
  kind: CollectionAxisKind,
  layers: CollectionLayer[],
): CollectionAxis | undefined {
  const built = axis(kind, layers);
  if (!built) return undefined;
  return {
    ...built,
    label:
      kind === "data"
        ? "Data dependant"
        : kind === "graph"
          ? "Graph dependant"
          : "Workflow dependant",
  };
}

function axesOf(
  list: Array<CollectionAxis | undefined>,
  empty: string,
): { axes: CollectionAxis[]; empty: string } {
  const axes = list.filter((entry): entry is CollectionAxis => Boolean(entry));
  return { axes, empty: axes.length ? "" : empty };
}

function workflowContext(
  index: ViewerIndex,
  component: string,
): { upstream: string[]; downstream: string[] } {
  const upstream = new Set<string>();
  const downstream = new Set<string>();
  for (const step of index.stepsByComponent.get(component) ?? []) {
    const key = step.id.join("\u0000");
    for (const connection of index.incomingByStepId.get(key) ?? []) {
      const producer = connection.outputStepId[0];
      if (producer !== component) upstream.add(producer);
    }
    for (const connection of index.outgoingByStepId.get(key) ?? []) {
      const consumer = connection.inputStepId[0];
      if (consumer !== component) downstream.add(consumer);
    }
  }
  return { upstream: [...upstream].sort(), downstream: [...downstream].sort() };
}

function workflowCells(row: WorkflowStepRow): string[] {
  return [
    row.kindLabel,
    `${row.inputs}`,
    `${row.outputs}`,
    `${row.connections}`,
  ];
}

function base(id: CollectionId, component?: string): CollectionModel {
  const definition = COLLECTIONS[id];
  const title = collectionTitle(id, component);
  return {
    id,
    component,
    concept: definition.concept,
    kicker: component ? "Workflow component" : definition.kicker,
    title,
    subtitle: component
      ? `Workflow component collection · ${component}`
      : `${definition.title} layer · a collection, not a declared subject`,
    facts: [],
    dependency: { axes: [], empty: "" },
    dependants: { axes: [], empty: "" },
    items: { columns: [], template: "", rows: [], empty: "" },
    coverage: [],
  };
}

function withFacts(
  model: CollectionModel,
  facts: { items: number; meaning: number; produced: number; consumed: number },
): CollectionModel {
  model.facts = [
    { label: "Items", value: `${facts.items}` },
    { label: "With meaning", value: `${facts.meaning}` },
    { label: "Produced", value: `${facts.produced}` },
    { label: "Consumed", value: `${facts.consumed}` },
  ];
  model.coverage = [
    {
      key: "items",
      measure: "Items",
      count: facts.items,
      reading: "members of this layer",
    },
    {
      key: "meaning",
      measure: "With meaning",
      count: facts.meaning,
      reading: "carry a purpose, claim or limitation",
    },
    {
      key: "produced",
      measure: "With a dependency",
      count: facts.produced,
      reading: "are produced by a lower layer",
    },
    {
      key: "consumed",
      measure: "With a dependant",
      count: facts.consumed,
      reading: "are read by a layer above",
    },
  ];
  return model;
}

function assetCollection(index: ViewerIndex): CollectionModel {
  const model = base("assets");
  const items = index.assets;
  const meaning = items.filter((asset) =>
    hasMeaning(asset.meaning ?? asset.semantics),
  ).length;
  const consumed = items.filter(
    (asset) => assetRelations(index, asset.name) > 0,
  ).length;

  model.dependency = axesOf(
    [],
    "Assets are the origin. No layer is below an asset.",
  );
  model.dependants = axesOf(
    [
      dependantAxis("data", [
        layer("data", "sourceRelations", "Source relations", "table", index.relations.length, {
          collection: { id: "sourceRelations" },
          note: "each source relation reads one asset",
        }),
      ]),
    ],
    "No source relation reads an asset.",
  );
  model.items = {
    columns: ["Asset", "Layout", "Source relations"],
    template: "minmax(180px, 1.6fr) minmax(90px, 0.7fr) 110px",
    empty: "No asset is declared.",
    rows: items.map((asset) => ({
      key: asset.name,
      concept: "asset",
      name: asset.name,
      cells: [
        asset.layout?.kind ?? "unspecified",
        `${assetRelations(index, asset.name)}`,
      ],
    })),
  };
  return withFacts(model, {
    items: items.length,
    meaning,
    produced: 0,
    consumed,
  });
}

function relationCollection(
  index: ViewerIndex,
  id: "sourceRelations" | "derivedRelations",
): CollectionModel {
  const model = base(id);
  const derived = id === "derivedRelations";
  const items = derived ? index.projections : index.relations;
  const sourceNames = new Set(index.relations.map((relation) => relation.name));
  const derivedNames = new Set(
    index.projections.map((projection) => projection.name),
  );
  const meaning = items.filter((item) =>
    hasMeaning(item.meaning ?? item.semantics),
  ).length;
  const produced = derived
    ? items.filter(
        (item) =>
          relationNamesFromRowSource(
            (item as ViewerIndex["projections"][number]).row_source,
          ).length > 0,
      ).length
    : items.filter((item) => Boolean(resolveAssetName(index, item.name))).length;
  const consumed = items.filter(
    (item) =>
      directDerived(index, item.name).length > 0 ||
      directBindings(index, item.name).length > 0,
  ).length;

  const dataDependency: CollectionLayer[] = derived
    ? [
        layer("data", "assets", "Assets", "asset", index.assets.length, {
          collection: { id: "assets" },
          note: "the origin of every value",
        }),
        layer("data", "sourceRelations", "Source relations", "table", index.relations.length, {
          collection: { id: "sourceRelations" },
          note: "the relations a derived relation scans",
        }),
      ]
    : [
        layer("data", "assets", "Assets", "asset", index.assets.length, {
          collection: { id: "assets" },
          note: "the origin of every value",
        }),
      ];
  dataDependency.push(
    derived
      ? layer("data", "derivedRelations", "Derived relations", "projection", index.projections.length, {
          current: true,
          note: "this collection",
        })
      : layer("data", "sourceRelations", "Source relations", "table", index.relations.length, {
          current: true,
          note: "this collection",
        }),
  );

  const derivedConsumers = index.projections.filter((projection) =>
    relationNamesFromRowSource(projection.row_source).some((name) =>
      derived ? derivedNames.has(name) : sourceNames.has(name),
    ),
  ).length;
  const bindingConsumers = index.bindings.filter((binding) =>
    relationNamesFromRowSource(binding.binding.rows).some((name) =>
      derived ? derivedNames.has(name) : sourceNames.has(name),
    ),
  ).length;

  model.dependency = axesOf([axis("data", dataDependency)], "");
  model.dependants = axesOf(
    [
      dependantAxis("data", [
        layer("data", "derivedConsumers", derived ? "Derived relations" : "Derived relations", "projection", derivedConsumers, {
          collection: { id: "derivedRelations" },
          note: derived
            ? "derived relations that scan this layer"
            : "derived relations that scan these relations",
        }),
        layer("data", "bindings", "Bindings", "binding", bindingConsumers, {
          collection: { id: "bindings" },
          note: "bindings that read this layer directly",
        }),
      ]),
    ],
    "No derived relation or binding reads this layer.",
  );

  model.items = derived
    ? {
        columns: ["Relation", "Asset", "Columns", "Scans", "Bindings"],
        template:
          "minmax(170px, 1.5fr) minmax(90px, 0.7fr) 70px minmax(120px, 1fr) 74px",
        empty: "No derived relation is declared.",
        rows: index.projections.map((projection) => ({
          key: projection.name,
          concept: "projection",
          name: projection.name,
          component: projection.name,
          cells: [
            resolveAssetName(index, projection.name) ?? "unresolved",
            `${projection.columns?.length ?? 0}`,
            relationNamesFromRowSource(projection.row_source).join(", ") || "—",
            `${directBindings(index, projection.name).length}`,
          ],
        })),
      }
    : {
        columns: ["Relation", "Asset", "Columns", "Dependants"],
        template: "minmax(180px, 1.5fr) minmax(110px, 0.9fr) 74px 100px",
        empty: "No source relation is declared.",
        rows: index.relations.map((relation) => ({
          key: relation.name,
          concept: "table",
          name: relation.name,
          component: relation.name,
          cells: [
            resolveAssetName(index, relation.name) ?? "unresolved",
            `${relation.columns?.length ?? 0}`,
            `${directDerived(index, relation.name).length + directBindings(index, relation.name).length}`,
          ],
        })),
      };
  return withFacts(model, {
    items: items.length,
    meaning,
    produced,
    consumed,
  });
}

function bindingsCollection(index: ViewerIndex): CollectionModel {
  const model = base("bindings");
  const items = index.bindings;
  const meaning = items.filter((binding) =>
    hasMeaning(bindingMeaning(binding)),
  ).length;
  const produced = items.filter(
    (binding) => relationNamesFromRowSource(binding.binding.rows).length > 0,
  ).length;
  const nodes = new Set(
    items.filter((binding) => binding.kind === "node").map((binding) => binding.component),
  );
  const edges = new Set(
    items.filter((binding) => binding.kind === "edge").map((binding) => binding.component),
  );
  const sourceNames = new Set(
    items.flatMap((binding) =>
      relationNamesFromRowSource(binding.binding.rows).filter((name) =>
        index.relationByName.has(name),
      ),
    ),
  );
  const derivedNames = new Set(
    items.flatMap((binding) =>
      relationNamesFromRowSource(binding.binding.rows).filter((name) =>
        index.projectionByName.has(name),
      ),
    ),
  );
  const assetNames = new Set(
    [...sourceNames, ...derivedNames]
      .map((name) => resolveAssetName(index, name))
      .filter((name): name is string => Boolean(name)),
  );

  model.dependency = axesOf(
    [
      axis("data", [
        layer("data", "assets", "Assets", "asset", assetNames.size, {
          collection: { id: "assets" },
          note: "assets behind the rows this layer reads",
        }),
        layer("data", "sourceRelations", "Source relations", "table", sourceNames.size, {
          collection: { id: "sourceRelations" },
          note: "source relations this layer reads",
        }),
        layer("data", "derivedRelations", "Derived relations", "projection", derivedNames.size, {
          collection: { id: "derivedRelations" },
          note: "derived relations this layer reads",
        }),
        layer("data", "bindings", "Bindings", "binding", items.length, {
          current: true,
          note: "this collection",
        }),
      ]),
    ],
    "No binding reads a relation.",
  );
  model.dependants = axesOf(
    [
      dependantAxis("data", [
        layer("data", "nodes", "Nodes", "node", nodes.size, {
          collection: { id: "nodes" },
          note: "records this layer writes",
        }),
        layer("data", "edges", "Edges", "edge", edges.size, {
          collection: { id: "edges" },
          note: "edges this layer writes",
        }),
      ]),
    ],
    "No record depends on a binding.",
  );
  model.items = {
    columns: ["Binding", "Record", "Rows read", "Writes"],
    template: "minmax(190px, 1.5fr) minmax(110px, 0.9fr) minmax(140px, 1.2fr) 64px",
    empty: "No binding is declared.",
    rows: items.map((binding) => ({
      key: `binding:${binding.index}`,
      concept: "binding",
      name: bindingName(binding),
      component: binding.component,
      ownerConcept: binding.kind,
      bindingIndex: binding.index,
      cells: [
        binding.component,
        relationNamesFromRowSource(binding.binding.rows).join(", ") || "—",
        `${Object.keys(binding.binding.properties ?? {}).length}`,
      ],
    })),
  };
  return withFacts(model, {
    items: items.length,
    meaning,
    produced,
    consumed: nodes.size + edges.size,
  });
}

function recordsCollection(
  index: ViewerIndex,
  id: "nodes" | "edges",
): CollectionModel {
  const model = base(id);
  const isEdge = id === "edges";
  const items = isEdge
    ? index.topologyEdges.filter((edge) => !edge.abstract)
    : index.topologyNodes.filter((node) => !node.abstract);
  const semanticKind = isEdge ? ("edge" as const) : ("node" as const);
  const bindings = index.bindings.filter((binding) => binding.kind === semanticKind);
  const targeted = new Set(items.map((item) => item.name));
  const relevantBindings = bindings.filter((binding) => targeted.has(binding.component));
  const sourceNames = new Set(
    relevantBindings.flatMap((binding) =>
      relationNamesFromRowSource(binding.binding.rows).filter((name) =>
        index.relationByName.has(name),
      ),
    ),
  );
  const derivedNames = new Set(
    relevantBindings.flatMap((binding) =>
      relationNamesFromRowSource(binding.binding.rows).filter((name) =>
        index.projectionByName.has(name),
      ),
    ),
  );
  const assetNames = new Set(
    [...sourceNames, ...derivedNames]
      .map((name) => resolveAssetName(index, name))
      .filter((name): name is string => Boolean(name)),
  );
  const meaning = items.filter((item) =>
    hasMeaning(item.meaning ?? item.semantics),
  ).length;
  const produced = items.filter((item) =>
    relevantBindings.some((binding) => binding.component === item.name),
  ).length;
  const consumed = isEdge
    ? 0
    : items.filter((node) =>
        index.topologyEdges.some(
          (edge) =>
            !edge.abstract &&
            (edge.source?.[2] === node.name || edge.target?.[2] === node.name),
        ),
      ).length;

  const dataDependency: CollectionLayer[] = [
    layer("data", "assets", "Assets", "asset", assetNames.size, {
      collection: { id: "assets" },
      note: "assets behind the bindings that write this layer",
    }),
    layer("data", "sourceRelations", "Source relations", "table", sourceNames.size, {
      collection: { id: "sourceRelations" },
      note: "source relations read by those bindings",
    }),
    layer("data", "derivedRelations", "Derived relations", "projection", derivedNames.size, {
      collection: { id: "derivedRelations" },
      note: "derived relations read by those bindings",
    }),
    layer("data", "bindings", "Bindings", "binding", relevantBindings.length, {
      collection: { id: "bindings" },
      note: "the bindings that write this layer",
    }),
    layer("data", "records", isEdge ? "Edges" : "Nodes", isEdge ? "edge" : "node", items.length, {
      current: true,
      note: "this collection",
    }),
  ];
  const graphDependency: CollectionLayer[] = isEdge
    ? [
        layer("graph", "abstract", "Abstract", "abstract", abstractCount(index), {
          collection: { id: "abstract" },
          note: "categories that own endpoints",
        }),
        layer("graph", "nodes", "Nodes", "node", index.topologyNodes.filter((node) => !node.abstract).length, {
          collection: { id: "nodes" },
          note: "records at the edge's endpoints",
        }),
      ]
    : [
        layer("graph", "graph", "Graph", "graph", 1, {
          note: "the graph declaration",
        }),
        layer("graph", "abstract", "Abstract", "abstract", abstractCount(index), {
          collection: { id: "abstract" },
          note: "categories above these records",
        }),
      ];

  model.dependency = axesOf(
    [axis("data", dataDependency), axis("graph", graphDependency)],
    "",
  );
  model.dependants = axesOf(
    [
      isEdge
        ? undefined
        : dependantAxis("graph", [
            layer("graph", "edges", "Edges", "edge", index.topologyEdges.filter((edge) => !edge.abstract).length, {
              collection: { id: "edges" },
              note: "edges incident on these nodes",
            }),
          ]),
    ],
    isEdge
      ? "No layer depends on an edge. Its endpoints are dependencies."
      : "No data layer depends on a record.",
  );

  model.items = isEdge
    ? {
        columns: ["Edge", "Endpoints", "Properties", "Bindings"],
        template: "minmax(180px, 1.4fr) minmax(150px, 1.3fr) 78px 74px",
        empty: "No edge is declared.",
        rows: index.topologyEdges
          .filter((edge) => !edge.abstract)
          .map((edge) => ({
            key: edge.name,
            concept: "edge",
            name: edge.name,
            component: edge.name,
            cells: [
              edge.source?.[2] && edge.target?.[2]
                ? `${edge.source[2]} → ${edge.target[2]}`
                : "unresolved",
              `${edge.properties?.length ?? 0}`,
              `${componentBindings(index, "edge", edge.name).length}`,
            ],
          })),
      }
    : {
        columns: ["Node", "Labels", "Properties", "Bindings"],
        template: "minmax(180px, 1.4fr) minmax(130px, 1fr) 80px 74px",
        empty: "No node is declared.",
        rows: index.topologyNodes
          .filter((node) => !node.abstract)
          .map((node) => ({
            key: node.name,
            concept: "node",
            name: node.name,
            component: node.name,
            cells: [
              (node.labels ?? []).join(", ") || "—",
              `${node.properties?.length ?? 0}`,
              `${componentBindings(index, "node", node.name).length}`,
            ],
          })),
      };
  return withFacts(model, {
    items: items.length,
    meaning,
    produced,
    consumed,
  });
}

function abstractCount(index: ViewerIndex): number {
  return (
    index.topologyNodes.filter((node) => node.abstract).length +
    index.topologyEdges.filter((edge) => edge.abstract).length
  );
}

function abstractCollection(index: ViewerIndex): CollectionModel {
  const model = base("abstract");
  const abstractNodes = index.topologyNodes.filter((node) => node.abstract);
  const abstractEdges = index.topologyEdges.filter((edge) => edge.abstract);
  const items = [
    ...abstractNodes.map((node) => ({
      name: node.name,
      concept: "abstract" as const,
      kind: "abstract node",
      bindings: componentBindings(index, "node", node.name),
    })),
    ...abstractEdges.map((edge) => ({
      name: edge.name,
      concept: "edge" as const,
      kind: "abstract edge",
      bindings: componentBindings(index, "edge", edge.name),
    })),
  ];
  const ownBindings = index.bindings.filter((binding) =>
    items.some((item) => item.name === binding.component),
  );
  const sourceNames = new Set(
    ownBindings.flatMap((binding) =>
      relationNamesFromRowSource(binding.binding.rows).filter((name) =>
        index.relationByName.has(name),
      ),
    ),
  );
  const derivedNames = new Set(
    ownBindings.flatMap((binding) =>
      relationNamesFromRowSource(binding.binding.rows).filter((name) =>
        index.projectionByName.has(name),
      ),
    ),
  );
  const assetNames = new Set(
    [...sourceNames, ...derivedNames]
      .map((name) => resolveAssetName(index, name))
      .filter((name): name is string => Boolean(name)),
  );
  const meaning = items.filter((item) => {
    const declaration = index.topologyComponentsByName.get(item.name);
    return hasMeaning(declaration?.meaning ?? declaration?.semantics);
  }).length;
  const produced = items.filter((item) => item.bindings.length > 0).length;
  const consumed = items.filter(
    (item) => immediateChildren(index, item.name).length > 0,
  ).length;

  model.dependency = axesOf(
    [
      axis("data", [
        layer("data", "assets", "Assets", "asset", assetNames.size, {
          collection: { id: "assets" },
          note: "assets behind the bindings of this layer",
        }),
        layer("data", "sourceRelations", "Source relations", "table", sourceNames.size, {
          collection: { id: "sourceRelations" },
          note: "source relations read by those bindings",
        }),
        layer("data", "derivedRelations", "Derived relations", "projection", derivedNames.size, {
          collection: { id: "derivedRelations" },
          note: "derived relations read by those bindings",
        }),
        layer("data", "bindings", "Bindings", "binding", ownBindings.length, {
          collection: { id: "bindings" },
          note: "the bindings that write abstract participants",
        }),
        layer("data", "abstract", "Abstract", "abstract", items.length, {
          current: true,
          note: "this collection",
        }),
      ]),
      axis("graph", [
        layer("graph", "graph", "Graph", "graph", 1, {
          note: "the graph declaration",
        }),
      ]),
    ],
    "",
  );
  const childLayers = [
    layer(
      "graph",
      "abstract",
      "Abstract",
      "abstract",
      items.filter(
        (item) =>
          item.concept === "abstract" &&
          index.topologyComponentsByName.get(item.name)?.parent?.[2] !==
            undefined,
      ).length,
      {
        collection: { id: "abstract" },
        note: "child categories",
      },
    ),
    layer("graph", "nodes", "Nodes", "node", abstractChildNodes(index), {
      collection: { id: "nodes" },
      note: "concrete records directly under a category",
    }),
    layer("graph", "edges", "Edges", "edge", abstractChildEdges(index), {
      collection: { id: "edges" },
      note: "edges directly under a category",
    }),
  ];
  model.dependants = axesOf(
    [dependantAxis("graph", childLayers)],
    "No child category, node or edge sits directly under an abstract participant.",
  );
  model.items = {
    columns: ["Item", "Kind", "Own bindings", "Immediate children"],
    template: "minmax(180px, 1.5fr) minmax(110px, 0.8fr) 92px 110px",
    empty: "No abstract participant is declared.",
    rows: items.map((item) => ({
      key: `${item.concept}:${item.name}`,
      concept: item.concept,
      name: item.name,
      component: item.name,
      cells: [
        item.kind,
        `${item.bindings.length}`,
        `${immediateChildren(index, item.name).length}`,
      ],
    })),
  };
  return withFacts(model, {
    items: items.length,
    meaning,
    produced,
    consumed,
  });
}

function abstractChildNodes(index: ViewerIndex): number {
  const abstract = new Set(
    index.topologyNodes.filter((node) => node.abstract).map((node) => node.name),
  );
  return index.topologyNodes.filter(
    (node) => !node.abstract && node.parent?.[2] && abstract.has(node.parent[2]),
  ).length;
}

function abstractChildEdges(index: ViewerIndex): number {
  const abstract = new Set([
    ...index.topologyNodes.filter((node) => node.abstract).map((node) => node.name),
    ...index.topologyEdges.filter((edge) => edge.abstract).map((edge) => edge.name),
  ]);
  return index.topologyEdges.filter(
    (edge) => !edge.abstract && edge.parent?.[2] && abstract.has(edge.parent[2]),
  ).length;
}

function workflowCollection(
  index: ViewerIndex,
  component?: string,
): CollectionModel {
  const model = base("workflow", component);
  const workflowRows = buildWorkflowModel(index).rows;
  if (!component) {
    const groups = groupWorkflowRows(workflowRows);
    model.subtitle = "Workflow layer · a collection of component groups";
    model.dependency = axesOf(
      [],
      "The workflow is the build root. No layer is below it.",
    );
    model.dependants = axesOf(
      [],
      "No layer depends on the whole workflow.",
    );
    model.items = {
      columns: ["Component", "Steps", "Kinds", "Connections"],
      template: "minmax(190px, 1.6fr) 80px 70px 100px",
      empty: "No workflow component is declared.",
      rows: groups.map((group) => ({
        key: group.component,
        concept: "workflow",
        name: group.component,
        cells: [
          `${group.rows.length}`,
          `${new Set(group.rows.map((row) => row.kindKey)).size}`,
          `${group.rows.reduce((total, row) => total + row.connections, 0)}`,
        ],
        collection: { id: "workflow", component: group.component },
      })),
    };
    return withFacts(model, {
      items: groups.length,
      meaning: 0,
      produced: 0,
      consumed: 0,
    });
  }

  const rows = workflowRows.filter((row) => row.component === component);
  const context = workflowContext(index, component);
  model.dependency = axesOf(
    [
      axis(
        "workflow",
        context.upstream.map((name) =>
          layer("workflow", `upstream:${name}`, name, "workflow", 1, {
            collection: { id: "workflow", component: name },
            note: "upstream component",
          }),
        ),
      ),
    ],
    "This component is a workflow root. No component feeds it.",
  );
  model.dependants = axesOf(
    [
      dependantAxis(
        "workflow",
        context.downstream.map((name) =>
          layer("workflow", `downstream:${name}`, name, "workflow", 1, {
            collection: { id: "workflow", component: name },
            note: "downstream component",
          }),
        ),
      ),
    ],
    "No component reads from this one.",
  );
  model.items = {
    columns: ["Step", "Instruction", "Inputs", "Outputs", "Connections"],
    template: "minmax(190px, 1.8fr) minmax(120px, 1.1fr) 64px 66px 92px",
    empty: "This component has no steps.",
    rows: rows.map((row) => ({
      key: row.key,
      concept: "step",
      name: row.name,
      component: row.component,
      stepId: row.id,
      cells: workflowCells(row),
    })),
  };
  return withFacts(model, {
    items: rows.length,
    meaning: 0,
    produced: rows.filter((row) => row.inputs > 0).length,
    consumed: rows.filter((row) => row.outputs > 0).length,
  });
}

/** Build the model for one virtual collection. */
export function collectionModel(
  index: ViewerIndex,
  id: CollectionId,
  component?: string,
): CollectionModel {
  switch (id) {
    case "assets":
      return assetCollection(index);
    case "sourceRelations":
      return relationCollection(index, "sourceRelations");
    case "derivedRelations":
      return relationCollection(index, "derivedRelations");
    case "bindings":
      return bindingsCollection(index);
    case "nodes":
      return recordsCollection(index, "nodes");
    case "edges":
      return recordsCollection(index, "edges");
    case "abstract":
      return abstractCollection(index);
    case "workflow":
      return workflowCollection(index, component);
  }
}


// ---------------------------------------------------------------------------
// Layer DAGs
// ---------------------------------------------------------------------------

function layerKind(concept: ConceptKind): PurposeLevelKind {
  switch (concept) {
    case "table":
      return "relation";
    case "workflow":
      return "step";
    case "semantics":
    case "field":
      return "graph";
    default:
      return concept;
  }
}

function layerFrame(concept: ConceptKind): ConstitutionFrameId {
  if (concept === "binding") return "fulfilment";
  if (concept === "table" || concept === "projection" || concept === "asset") {
    return "relation";
  }
  return "graph";
}

function collectionPurpose(model: CollectionModel): ConstitutionNode {
  return {
    kind: layerKind(model.concept),
    name: model.title,
    label: "Collection",
    meaning: EMPTY_MEANING,
    current: true,
    detail: `${model.items.rows.length} items`,
    text: `${model.items.rows.length} items · this collection`,
    collection: { id: model.id, component: model.component },
    component: model.component,
    frame: layerFrame(model.concept),
  };
}

function nodeKey(node: ConstitutionNode): string {
  if (node.kind === "binding" && node.bindingIndex !== undefined) {
    return `binding:${node.bindingIndex}`;
  }
  return `${node.kind}:${node.name}`;
}

function collectionItems(model: CollectionModel): ConstitutionSubjectLike[] {
  const items: ConstitutionSubjectLike[] = [];
  for (const row of model.items.rows) {
    switch (row.concept) {
      case "asset":
        items.push({ level: "asset", component: row.name });
        break;
      case "table":
        items.push({ level: "relation", component: row.name });
        break;
      case "projection":
        items.push({ level: "projection", component: row.name });
        break;
      case "binding":
        if (row.bindingIndex !== undefined) {
          items.push({
            level: "binding",
            component: row.component ?? row.name,
            name: row.name,
            bindingIndex: row.bindingIndex,
          });
        }
        break;
      case "node":
        items.push({ level: "node", component: row.name });
        break;
      case "abstract":
        items.push({ level: "abstract", component: row.name });
        break;
      case "edge":
        items.push({ level: "edge", component: row.name });
        break;
      case "step":
        if (row.stepId) {
          items.push({
            level: "step",
            component: row.stepId[0],
            name: row.name,
            stepId: row.stepId,
          });
        }
        break;
      default:
        break;
    }
  }
  return items;
}

function bindingNode(
  binding: ConstitutionBinding,
  frame: ConstitutionFrameId,
): ConstitutionNode {
  return {
    kind: "binding",
    name: binding.name,
    label: "Binding",
    meaning: binding.meaning,
    component: binding.component,
    bindingIndex: binding.index,
    frame,
  };
}

/** A collection boundary is bounded by a readable number of actual subjects. */
const COLLECTION_SUBJECT_LIMIT = 80;

/**
 * One item and its boundary: the actual item subject plus the participants
 * merged from its constitution or contribution.
 */
function itemBoundary(
  index: ViewerIndex,
  item: ConstitutionSubjectLike,
  direction: "dependency" | "contribution",
  frame: ConstitutionFrameId,
): {
  nodes: Map<string, ConstitutionNode>;
  edges: Map<string, { source: string; target: string }>;
} {
  const nodes = new Map<string, ConstitutionNode>();
  const edges = new Map<string, { source: string; target: string }>();
  const addNode = (node: ConstitutionNode): string => {
    const copy: ConstitutionNode = {
      ...node,
      current: false,
      collection: undefined,
      frame,
    };
    const id = nodeKey(copy);
    nodes.set(id, copy);
    return id;
  };
  const addEdge = (source: string, target: string) => {
    edges.set(`${source}->${target}`, { source, target });
  };
  const addRelation = (relation: ConstitutionRelation): string => {
    const id = addNode(relation.node);
    for (const child of relation.children) {
      const childId = addRelation(child);
      addEdge(childId, id);
    }
    return id;
  };

  const boundary =
    item.level === "step"
      ? stepBoundaryModel(index, item, direction)
      : direction === "dependency"
        ? constitutionModel(index, item)
        : contributionModel(index, item, { collapse: false });
  const itemNode: ConstitutionNode = {
    ...boundary.subject,
    current: false,
    item: true,
    collection: undefined,
    frame,
    ...(item.level === "binding" && item.bindingIndex !== undefined
      ? { component: item.component, bindingIndex: item.bindingIndex }
      : {}),
    ...(item.stepId
      ? { component: item.stepId[0], stepId: item.stepId }
      : {}),
  };
  const itemId = addNode(itemNode);

  boundary.graph.forEach(addNode);
  const relationRoots = boundary.relation.map((relation) => ({
    node: relation.node,
    id: addRelation(relation),
  }));
  boundary.bindings.forEach((binding) => addNode(bindingNode(binding, frame)));
  (boundary.workflow ?? []).forEach(addNode);

  if (direction === "dependency") {
    boundary.graph.forEach((node, position) => {
      const target =
        position === 0 ? itemId : nodeKey(boundary.graph[position - 1]);
      addEdge(nodeKey(node), target);
    });
    for (const binding of boundary.bindings) {
      const bindingId = `binding:${binding.index}`;
      addEdge(bindingId, itemId);
      for (const relationName of binding.relations) {
        const root = relationRoots.find(
          (entry) => entry.node.name === relationName,
        );
        if (root) addEdge(root.id, bindingId);
      }
    }
    if (!boundary.bindings.length) {
      relationRoots.forEach((root) => addEdge(root.id, itemId));
    }
    (boundary.workflow ?? []).forEach((node) =>
      addEdge(nodeKey(node), itemId),
    );
  } else {
    boundary.graph.forEach((node) => addEdge(itemId, nodeKey(node)));
    relationRoots.forEach((root) => addEdge(itemId, root.id));
    boundary.bindings.forEach((binding) =>
      addEdge(itemId, `binding:${binding.index}`),
    );
    (boundary.workflow ?? []).forEach((node) =>
      addEdge(itemId, nodeKey(node)),
    );
  }

  return { nodes, edges };
}

/**
 * Read a collection through its actual subjects. There is no collection root:
 * the boxes are the collection's items plus the real participants merged from
 * their constitutions or contributions. Shared declarations are one box. Items
 * are accepted until the boundary reaches a readable size; the card states how
 * many items are shown.
 */
export function collectionDagModel(
  index: ViewerIndex,
  model: CollectionModel,
  direction: "dependency" | "contribution",
): ConstitutionModel {
  const frame = layerFrame(model.concept);
  const items = collectionItems(model);
  const nodes = new Map<string, ConstitutionNode>();
  const edges = new Map<string, { source: string; target: string }>();
  let accepted = 0;

  for (const item of items) {
    const part = itemBoundary(index, item, direction, frame);
    const union = new Set([...nodes.keys(), ...part.nodes.keys()]);
    if (accepted > 0 && union.size > COLLECTION_SUBJECT_LIMIT) break;
    part.nodes.forEach((node, key) => nodes.set(key, node));
    part.edges.forEach((edge, key) => edges.set(key, edge));
    accepted += 1;
  }

  const layers = [...nodes.values()];
  const kept = new Set(layers.map(nodeKey));
  const layerEdges = [...edges.values()].filter(
    (edge) => kept.has(edge.source) && kept.has(edge.target),
  );
  const note =
    accepted < items.length
      ? `Showing ${accepted} of ${items.length} items and their boundary.`
      : direction === "dependency"
        ? model.dependency.empty
        : model.dependants.empty;
  return {
    subjectSet: true,
    direction,
    subject: collectionPurpose(model),
    graph: [],
    relation: [],
    bindings: [],
    layers,
    layerEdges,
    note,
  };
}

/** Build the model for one virtual collection. */
