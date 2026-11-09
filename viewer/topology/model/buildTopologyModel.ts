import type { CampaignView } from "@/shared/model/campaign";
import type { IconToken } from "@/shared/model/hierarchy";
import type { LogicalType, TopologyEdge, TopologyNode } from "@/lib/types";
import type {
  TopologyGroupModel,
  TopologyLinkModel,
  TopologyModel,
  TopologyNavigatorRow,
  TopologyNavigatorSection,
  TopologyNeighbourModel,
  TopologyNodeModel,
  TopologyPropertyModel,
  TopologySelection,
  TopologySelectionCommands,
  TopologySelectionModel,
} from "./TopologyModel";
import { buildPropertyBadges } from "./propertyBadges";

function parentGroup(value: TopologyNode | TopologyEdge): string {
  const parent = value.parent?.at(-1);
  return parent && parent.trim() ? parent : "uncategorized";
}

function typeLabel(type: LogicalType | undefined): string {
  if (!type) return "";
  if (type.kind === "array") {
    return `${typeLabel(type.item) || "item"}[]`;
  }
  if (type.name) return type.name;
  if (type.kind === "unit") return "value";
  return type.kind;
}

function action(
  id: string,
  label: string,
  icon: IconToken,
  run: () => void,
  title?: string,
) {
  return { id, label, icon, title, run };
}

function field(id: string, label: string, value: string | number) {
  return { id, label, value: String(value) };
}

/**
 * Build the Orientation model.
 *
 * Graph layout, viewport, pan/zoom, hover and the local group filter stay in
 * the view. This builder owns the topology nodes, links, groups, the selected
 * subject, its navigator sections and the commands that change the campaign
 * selection or open another panel.
 */
export function buildTopologyModel(
  campaign: CampaignView,
  selectionOverride?: TopologySelection | null,
): TopologyModel {
  const index = campaign.record.index;
  const audit = campaign.record.audit ?? undefined;

  const nodes: TopologyNodeModel[] = index.topologyNodes.map((value) => ({
    id: value.name,
    name: value.name,
    group: parentGroup(value),
    abstract: Boolean(value.abstract),
    degree: 0,
  }));
  const byName = new Map(nodes.map((node) => [node.name, node]));
  const links: TopologyLinkModel[] = [];

  for (const edge of index.topologyEdges) {
    const source = edge.source?.[2];
    const target = edge.target?.[2];
    if (!source || !target || !byName.has(source) || !byName.has(target)) continue;
    links.push({
      id: `edge:${edge.name}`,
      edgeName: edge.name,
      source,
      target,
    });
    byName.get(source)!.degree += 1;
    byName.get(target)!.degree += 1;
  }

  const groupCounts = new Map<string, number>();
  for (const node of nodes) {
    groupCounts.set(node.group, (groupCounts.get(node.group) ?? 0) + 1);
  }
  const groups: TopologyGroupModel[] = [...groupCounts.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, count]) => ({ id: name, name, count }));

  const busiestNode = nodes.reduce<TopologyNodeModel | undefined>(
    (best, node) => (best && best.degree >= node.degree ? best : node),
    undefined,
  );
  const busiest: TopologySelection | undefined = busiestNode
    ? { kind: "node", name: busiestNode.name }
    : undefined;
  const defaultSelection: TopologySelection | undefined = byName.has("target")
    ? { kind: "node", name: "target" }
    : undefined;

  const requested: TopologySelection | undefined =
    campaign.selection?.kind === "topology"
      ? {
          kind: campaign.selection.entityKind,
          name: campaign.selection.name,
        }
      : undefined;
  const exists = (value: TopologySelection | undefined): boolean =>
    Boolean(
      value &&
        (value.kind === "node"
          ? index.topologyNodesByName.has(value.name)
          : index.topologyEdgesByName.has(value.name)),
    );
  const selected =
    selectionOverride === null
      ? undefined
      : selectionOverride
        ? selectionOverride
        : exists(requested)
          ? requested
          : defaultSelection;
  const selectedEntity = selected
    ? selected.kind === "node"
      ? index.topologyNodesByName.get(selected.name)
      : index.topologyEdgesByName.get(selected.name)
    : undefined;

  const commands: TopologySelectionCommands = {
    selectNode: (name) =>
      campaign.commands.select({ kind: "topology", entityKind: "node", name }),
    selectEdge: (name) =>
      campaign.commands.select({ kind: "topology", entityKind: "edge", name }),
    clear: () => campaign.commands.select(null),
  };

  const neighbours: TopologyNeighbourModel[] = (() => {
    if (!selected) return [];
    if (selected.kind === "node") {
      const connected: Array<{ name: string; edge: string; direction: "out" | "in" }> = [];
      for (const link of links) {
        if (link.source === selected.name) {
          connected.push({ name: link.target, edge: link.edgeName, direction: "out" });
        } else if (link.target === selected.name) {
          connected.push({ name: link.source, edge: link.edgeName, direction: "in" });
        }
      }
      return connected
        .sort((left, right) => left.name.localeCompare(right.name))
        .map((entry) => ({
          id: `${entry.direction}:${entry.edge}:${entry.name}`,
          ...entry,
        }));
    }
    const link = links.find((candidate) => candidate.edgeName === selected.name);
    if (!link) return [];
    return [
      {
        id: `out:${link.edgeName}:${link.target}`,
        name: link.target,
        edge: link.edgeName,
        direction: "out",
      },
      {
        id: `in:${link.edgeName}:${link.source}`,
        name: link.source,
        edge: link.edgeName,
        direction: "in",
      },
    ];
  })();

  const focusNames = new Set<string>();
  if (selected) {
    if (selected.kind === "node") focusNames.add(selected.name);
    for (const neighbour of neighbours) focusNames.add(neighbour.name);
  }
  const focusedCount = focusNames.size;

  const reviewCount =
    audit && selectedEntity && selected
      ? audit.findings.filter(
          (finding) =>
            finding.subject?.kind === selected.kind &&
            (finding.subject.component ?? finding.subject.name) ===
              selectedEntity.name,
        ).length
      : 0;

  const propertyModels: TopologyPropertyModel[] = (selectedEntity?.properties ?? []).map(
    (property) => ({
      id: `property:${property.name}`,
      name: property.name,
      typeLabel: typeLabel(property.logical_type),
      title: property.description ?? "Open property lineage",
      badges: selected
        ? buildPropertyBadges(
            index,
            audit,
            selected.kind,
            selectedEntity?.name ?? "",
            property.name,
          )
        : [],
    }),
  );

  const selectionModel: TopologySelectionModel | undefined =
    selected && selectedEntity
      ? (() => {
          const edge =
            selected.kind === "edge"
              ? index.topologyEdgesByName.get(selected.name)
              : undefined;
          return {
            kind: selected.kind,
            name: selectedEntity.name,
            group: selected.kind === "edge" ? "relationship" : parentGroup(selectedEntity),
            abstract: selectedEntity.abstract,
            description: selectedEntity.description,
            labels: selectedEntity.labels ?? [],
            annotations: selectedEntity.annotations ?? [],
            properties: propertyModels,
            neighbours,
            reviewCount,
            relationship:
              edge?.source?.at(-1) && edge?.target?.at(-1)
                ? {
                    source: edge.source.at(-1) as string,
                    target: edge.target.at(-1) as string,
                  }
                : undefined,
            linkCount: neighbours.length,
            propertyCount: propertyModels.length,
            annotationCount: selectedEntity.annotations?.length ?? 0,
          };
        })()
      : undefined;

  const selectionSection: TopologyNavigatorSection = selectionModel
    ? {
        id: "selection",
        title: "Selection",
        question: "Which topology subject is selected?",
        count: "1",
        rows: [
          {
            id: `selection:${selectionModel.kind}:${selectionModel.name}`,
            kind: "selection",
            label: selectionModel.name,
            meta: selectionModel.kind,
            selected: true,
            abstract: selectionModel.abstract,
            actions: [
              action(
                "open-entity",
                selectionModel.name,
                "open",
                () =>
                  campaign.commands.select({
                    kind: "topology",
                    entityKind: selectionModel.kind,
                    name: selectionModel.name,
                  }),
                `Open ${selectionModel.name} in Explorer`,
              ),
            ],
          },
        ],
        fields: [
          field("group", "group", selectionModel.group),
          ...(selectionModel.relationship
            ? [
                field(
                  "relationship",
                  "relationship",
                  `${selectionModel.relationship.source} → ${selectionModel.relationship.target}`,
                ),
              ]
            : []),
          field("links", "links", selectionModel.linkCount),
          field("properties", "properties", selectionModel.propertyCount),
          field("annotations", "annotations", selectionModel.annotationCount),
        ],
        actions: [
          action(
            "review",
            "review",
            "question",
            () =>
              campaign.commands.openReview({
                kind: selectionModel.kind,
                name: selectionModel.name,
                component: selectionModel.name,
                entityKind: selectionModel.kind,
              }),
            "Open this subject in review",
          ),
        ],
        annotations: {
          annotations: selectionModel.annotations,
          context: {
            kind: selectionModel.kind,
            component: selectionModel.name,
          },
        },
        description: selectionModel.description,
        chips: selectionModel.labels,
        reviewCount: selectionModel.reviewCount,
      }
    : {
        id: "selection",
        title: "Selection",
        question: "Which topology subject is selected?",
        count: "0",
        rows: [],
        fields: [
          field("node-types", "node types", index.stats.topologyNodes),
          field("edge-types", "edge types", index.stats.topologyEdges),
        ],
        actions: busiest
          ? [
              action(
                "select-busiest",
                "busiest node",
                "navigator",
                () => commands.selectNode(busiest.name),
                `Select busiest node ${busiest.name}`,
              ),
            ]
          : [],
        empty: "nothing selected · pick a bubble or relationship wire",
      };

  const groupsSection: TopologyNavigatorSection = {
    id: "groups",
    title: "Groups",
    question: "Which parent group filters the topology?",
    count: String(groups.length),
    rows: groups.map((group) => ({
      id: `group:${group.id}`,
      kind: "group",
      label: group.name,
      meta: String(group.count),
    })),
  };

  const propertiesSection: TopologyNavigatorSection = {
    id: "properties",
    title: "Properties",
    question: "Which properties define the selected subject?",
    count: String(propertyModels.length),
    rows: propertyModels.map((property) => ({
      id: property.id,
      kind: "property",
      label: property.name,
      meta: property.typeLabel,
      title: property.title,
      badges: property.badges,
      actions:
        selected && selectedEntity
          ? [
              action(
                "open-property",
                property.name,
                "trace",
                () =>
                  campaign.commands.selectProperty(
                    selected.kind,
                    selectedEntity.name,
                    property.name,
                  ),
                property.title,
              ),
            ]
          : [],
    })),
    empty: "no properties",
  };

  const neighbourRows: TopologyNavigatorRow[] = neighbours.map((neighbour) => ({
    id: neighbour.id,
    kind: "neighbour",
    label: neighbour.name,
    meta: neighbour.edge,
    edge: neighbour.edge,
    direction: neighbour.direction,
    actions: [
      action(
        "select-node",
        neighbour.name,
        neighbour.direction === "out" ? "navigator" : "branch",
        () => commands.selectNode(neighbour.name),
        `Select ${neighbour.name}`,
      ),
      action(
        "select-edge",
        neighbour.edge,
        "branch",
        () => commands.selectEdge(neighbour.edge),
        `Select relationship ${neighbour.edge}`,
      ),
    ],
  }));

  const neighboursSection: TopologyNavigatorSection = {
    id: "neighbours",
    title: "Neighbours",
    question: "Which entities and relationships are adjacent?",
    count: String(neighbours.length),
    rows: neighbourRows,
    notice:
      neighbours.length > 8
        ? `${neighbours.length} neighbours · list scrolls with the panel`
        : undefined,
    empty: "no neighbours",
  };

  const navigatorSections: TopologyNavigatorSection[] = [
    selectionSection,
    groupsSection,
    propertiesSection,
    neighboursSection,
  ];
  const navigator = Object.assign(navigatorSections, {
    id: "navigator" as const,
    title: "Navigator" as const,
    meta: `${nodes.length} nodes · ${links.length} links`,
    sections: navigatorSections,
  });

  return {
    id: "topology",
    title: "Orientation",
    icon: "map",
    meta: "topology",
    hint: "drag to pan · scroll to zoom",
    stats: {
      nodes: nodes.length,
      links: links.length,
      nodeTypes: index.stats.topologyNodes,
      edgeTypes: index.stats.topologyEdges,
    },
    canvas: {
      graphKey: `${campaign.record.snapshot.name}:${nodes.length}:${links.length}:${groups.length}`,
      nodes,
      links,
      groups,
      selected,
      defaultSelection,
      busiest,
      focusedCount,
      reviewCount,
      selection: commands,
    },
    navigator,
    navigatorFor: (selection) =>
      buildTopologyModel(campaign, selection ?? null).navigator,
    metaGraph: index.metaGraph,
  };
}
