/**
 * The constitution as one directed acyclic graph: how the subject comes to be.
 *
 * A record is one DAG: its graph ancestry sits on the left, its relation
 * provenance on the right, and its binding nodes between them inside the
 * fulfilment frame. A relation, binding or asset has the subject's purpose at
 * the top and only the declarations that produce it below. The graph is laid
 * out by dagre as a layered DAG, so ranks, ordering and edge routes are
 * computed rather than hand-placed. A declaration is one node: a source
 * relation or asset shared by several consumers appears once and carries one
 * edge per consumer. Every edge points from the supply to the consumer.
 */

import { graphlib, layout } from "@dagrejs/dagre";

import type {
  ConstitutionBinding,
  ConstitutionModel,
  ConstitutionNode,
  ConstitutionRelation,
} from "../model/constitution";

export interface ConstitutionSceneNode {
  id: string;
  axis: "purpose" | "binding" | "graph" | "relation";
  node: ConstitutionNode;
  /** The binding's purpose, shown instead of the node's own purpose. */
  text?: string;
  hoverable?: boolean;
  /** The pill's owner and binding identity for navigation. */
  component?: string;
  bindingIndex?: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ConstitutionSceneEdge {
  id: string;
  source: string;
  target: string;
  path: string;
  /** The arrowhead tip and direction, in scene coordinates. */
  head?: { x: number; y: number; angle: number };
}

export interface ConstitutionSceneLabel {
  text: string;
  x: number;
  y: number;
}

export interface ConstitutionSceneNote {
  text: string;
  x: number;
  y: number;
}

/** One frame: the graph, relation or fulfilment group. */
export interface ConstitutionSceneFrame {
  id: "graph" | "fulfilment" | "relation";
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface ConstitutionScene {
  nodes: ConstitutionSceneNode[];
  edges: ConstitutionSceneEdge[];
  labels: ConstitutionSceneLabel[];
  notes: ConstitutionSceneNote[];
  /** The graph, fulfilment and relation frames present on this subject. */
  frames: ConstitutionSceneFrame[];
  /** The renderer translates the scene so frame padding stays visible. */
  offset: { x: number; y: number };
  width: number;
  height: number;
}

const NODE = {
  purpose: { width: 440, height: 108 },
  binding: { width: 300, height: 104 },
  graph: { width: 440, height: 104 },
  relation: { width: 300, height: 104 },
} as const;

const FRAME_PAD = 8;
const FRAME_TOP = 28;
const FRAME_LABEL_INSET = 12;
const FRAME_LABEL_BASELINE = 16;
const NOTE_GAP = 24;
const NOTE_HEIGHT = 24;

/** dagre's layered engine: top-to-bottom edges read bottom-to-top. */
const RANKDIR = "BT";
const NODE_SEP = 24;
const RANK_SEP = 48;

export function sceneNodeId(node: ConstitutionNode): string {
  return `${node.kind}:${node.name}`;
}

/** dagre edge points are already routed; keep them as one polyline. */
function routedPath(
  points: ReadonlyArray<{ x: number; y: number }>,
  dx: number,
  dy: number,
): string {
  return points
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${point.x + dx} ${point.y + dy}`,
    )
    .join(" ");
}

interface LayeredNode {
  id: string;
  width: number;
  height: number;
}

interface LayeredEdge {
  source: string;
  target: string;
}

interface LayeredLayout {
  positions: Map<string, { x: number; y: number }>;
  paths: Map<string, string>;
  width: number;
  height: number;
}

/**
 * Lay out one layered DAG and translate it into the scene by `offset`.
 *
 * The scene supplies nodes, edges and any rank constraint; dagre computes the
 * ranks, the ordering within a rank and the edge routes. The result is bound
 * to the origin so the caller only adds its document anchors.
 */
function layeredLayout(
  nodes: LayeredNode[],
  edges: LayeredEdge[],
  offset: { x: number; y: number } = { x: 0, y: 0 },
): LayeredLayout {
  const graph = new graphlib.Graph();
  graph.setGraph({ rankdir: RANKDIR, nodesep: NODE_SEP, ranksep: RANK_SEP });
  graph.setDefaultEdgeLabel(() => ({}));
  nodes.forEach((node) =>
    graph.setNode(node.id, { width: node.width, height: node.height }),
  );
  edges.forEach((edge) => graph.setEdge(edge.source, edge.target));
  layout(graph);

  const placed = nodes.map((node) => {
    const position = graph.node(node.id);
    return {
      node,
      left: position.x - node.width / 2,
      top: position.y - node.height / 2,
      right: position.x + node.width / 2,
      bottom: position.y + node.height / 2,
    };
  });
  const minX = Math.min(...placed.map((entry) => entry.left));
  const minY = Math.min(...placed.map((entry) => entry.top));
  const maxX = Math.max(...placed.map((entry) => entry.right));
  const maxY = Math.max(...placed.map((entry) => entry.bottom));
  const dx = offset.x - minX;
  const dy = offset.y - minY;

  const positions = new Map(
    placed.map((entry) => [
      entry.node.id,
      { x: entry.left + dx, y: entry.top + dy },
    ]),
  );
  const paths = new Map<string, string>();
  edges.forEach((edge) => {
    const routed = graph.edge(edge.source, edge.target);
    if (!routed?.points?.length) return;
    paths.set(
      `${edge.source}->${edge.target}`,
      routedPath(routed.points, dx, dy),
    );
  });
  return { positions, paths, width: maxX - minX, height: maxY - minY };
}

interface RelationProvenance {
  nodes: Map<string, ConstitutionNode>;
  roots: string[];
  down: Array<{ parent: string; child: string }>;
}

function relationProvenance(
  relations: ConstitutionRelation[],
): RelationProvenance {
  const nodes = new Map<string, ConstitutionNode>();
  const roots: string[] = [];
  const down: Array<{ parent: string; child: string }> = [];
  const downKeys = new Set<string>();
  const walk = (relation: ConstitutionRelation, parent?: string) => {
    const id = sceneNodeId(relation.node);
    nodes.set(id, relation.node);
    if (parent) {
      const key = `${parent}->${id}`;
      if (!downKeys.has(key)) {
        downKeys.add(key);
        down.push({ parent, child: id });
      }
    } else if (!roots.includes(id)) {
      roots.push(id);
    }
    relation.children.forEach((child) => walk(child, id));
  };
  relations.forEach((relation) => walk(relation));
  return { nodes, roots, down };
}

function bindingNode(binding: ConstitutionBinding): ConstitutionSceneNode {
  const node: ConstitutionNode = {
    kind: "binding",
    name: binding.name,
    label: "Binding",
    meaning: binding.meaning,
  };
  return {
    id: `binding:${binding.index}`,
    axis: "binding",
    node,
    component: binding.component,
    bindingIndex: binding.index,
    text: binding.purpose ?? binding.meaning.purpose ?? "No purpose is stated.",
    hoverable: Boolean(
      binding.meaning.purpose ||
        binding.meaning.claims.length ||
        binding.meaning.limitations.length ||
        (binding.meaning.frames?.length ?? 0),
    ),
    x: 0,
    y: 0,
    ...NODE.binding,
  };
}

function relationNode(node: ConstitutionNode): ConstitutionSceneNode {
  return {
    id: sceneNodeId(node),
    axis: "relation",
    node,
    x: 0,
    y: 0,
    ...NODE.relation,
  };
}

/** A relation the bindings read supplies the binding that reads it. */
function bindingRelationEdges(
  model: ConstitutionModel,
  rootByName: Map<string, string>,
): Array<{ source: string; target: string }> {
  const edges: Array<{ source: string; target: string }> = [];
  const seen = new Set<string>();
  model.bindings.forEach((binding) => {
    for (const name of binding.relations) {
      const rootId = rootByName.get(name);
      if (!rootId) continue;
      const target = `binding:${binding.index}`;
      const key = `${rootId}->${target}`;
      if (seen.has(key)) continue;
      seen.add(key);
      edges.push({ source: rootId, target });
    }
  });
  return edges;
}

/**
 * A binding sits beside the purpose. Its edge rises from the binding top into
 * its own lane, angles across the row and enters the purpose's right edge at a
 * distinct point, so no segment crosses another binding box.
 */
function bindingToPurposePath(
  binding: ConstitutionSceneNode,
  purpose: ConstitutionSceneNode,
  entryY: number,
  laneY: number,
): string {
  const startX = binding.x + binding.width / 2;
  const startY = binding.y;
  const endX = purpose.x + purpose.width;
  const bend = 24;
  return `M ${startX} ${startY} L ${startX} ${laneY} L ${
    endX + bend
  } ${entryY} L ${endX} ${entryY}`;
}

/** A produced subject enters the purpose's bottom edge at its assigned point. */
function componentToPurposePath(
  source: ConstitutionSceneNode,
  purpose: ConstitutionSceneNode,
  entryX: number,
): string {
  return `M ${source.x + source.width / 2} ${source.y} L ${entryX} ${
    purpose.y + purpose.height
  }`;
}

/** The ancestry supplies the purpose from below, in the same column. */
function ancestryToPurposePath(
  ancestor: ConstitutionSceneNode,
  purpose: ConstitutionSceneNode,
): string {
  return `M ${ancestor.x + ancestor.width / 2} ${ancestor.y} L ${
    purpose.x + purpose.width / 2
  } ${purpose.y + purpose.height}`;
}

/** The last segment gives the arrowhead tip and direction. */
function edgeHead(
  path: string,
): ConstitutionSceneEdge["head"] | undefined {
  const values = path.match(/-?\d+(?:\.\d+)?/g)?.map(Number);
  if (!values || values.length < 4) return undefined;
  const x1 = values[values.length - 4];
  const y1 = values[values.length - 3];
  const x2 = values[values.length - 2];
  const y2 = values[values.length - 1];
  return {
    x: x2,
    y: y2,
    angle: (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI,
  };
}

/** Replace the final point of a routed polyline. */
function moveEdgeEnd(path: string, x: number, y: number): string {
  return path.replace(
    /(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s*$/,
    `${x} ${y}`,
  );
}

/**
 * Every consumer edge enters its target on one centred, evenly spaced set of
 * points along the target's bottom edge. The purpose is routed explicitly by
 * the scene and is skipped here.
 */
function distributeConnections(
  edges: ConstitutionSceneEdge[],
  nodes: ConstitutionSceneNode[],
  skip: Set<string>,
): void {
  const byId = new Map(nodes.map((node) => [node.id, node]));
  const groups = new Map<string, ConstitutionSceneEdge[]>();
  for (const edge of edges) {
    if (skip.has(edge.target)) continue;
    const group = groups.get(edge.target) ?? [];
    group.push(edge);
    groups.set(edge.target, group);
  }
  for (const [targetId, group] of groups) {
    const target = byId.get(targetId);
    if (!target) continue;
    group.sort((left, right) => {
      const leftSource = byId.get(left.source);
      const rightSource = byId.get(right.source);
      return (
        (leftSource ? leftSource.x + leftSource.width / 2 : 0) -
        (rightSource ? rightSource.x + rightSource.width / 2 : 0)
      );
    });
    const count = group.length;
    const spacing =
      count > 1
        ? Math.min(24, (target.width - 32) / (count - 1))
        : 0;
    const centre = target.x + target.width / 2;
    group.forEach((edge, index) => {
      const entryX =
        centre + (index - (count - 1) / 2) * spacing;
      edge.path = moveEdgeEnd(
        edge.path,
        entryX,
        target.y + target.height,
      );
      edge.head = edgeHead(edge.path);
    });
  }
}

/** The padded bounds of one group: a topology-style category frame. */
function frameFor(
  id: ConstitutionSceneFrame["id"],
  members: ConstitutionSceneNode[],
): ConstitutionSceneFrame | undefined {
  if (!members.length) return undefined;
  const minX = Math.min(...members.map((node) => node.x)) - FRAME_PAD;
  const minY = Math.min(...members.map((node) => node.y)) - FRAME_TOP;
  const maxX =
    Math.max(...members.map((node) => node.x + node.width)) + FRAME_PAD;
  const maxY =
    Math.max(...members.map((node) => node.y + node.height)) + FRAME_PAD;
  return { id, x: minX, y: minY, width: maxX - minX, height: maxY - minY };
}

/** A subject whose constitution is its own purpose over its components. */
function isComponentsSubject(kind: ConstitutionNode["kind"]): boolean {
  return (
    kind === "relation" ||
    kind === "projection" ||
    kind === "binding" ||
    kind === "asset"
  );
}

/**
 * A record's constitution: one DAG whose graph ancestry sits on the left and
 * whose relation provenance sits on the right. The binding nodes connect the
 * two sides and are enclosed by the fulfilment frame. The graph purpose and the
 * bindings converge on the purpose; no separator or axis frame divides them.
 */
function buildRecordScene(model: ConstitutionModel): ConstitutionScene {
  const nodes: ConstitutionSceneNode[] = [];
  const edges: ConstitutionSceneEdge[] = [];
  const labels: ConstitutionSceneLabel[] = [];
  const notes: ConstitutionSceneNote[] = [];

  const purpose: ConstitutionSceneNode = {
    id: "purpose",
    axis: "purpose",
    node: model.purpose,
    x: 0,
    y: 0,
    ...NODE.purpose,
  };
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: 0,
    ...NODE.graph,
  }));
  const bindings = model.bindings.map(bindingNode);
  const provenance = relationProvenance(model.relation);
  const relations = [...provenance.nodes.values()].map(relationNode);
  const dagreNodes = [purpose, ...graphNodes, ...bindings, ...relations];

  const rootByName = new Map<string, string>();
  provenance.roots.forEach((id) => {
    const node = provenance.nodes.get(id);
    if (node) rootByName.set(node.name, id);
  });

  const links: LayeredEdge[] = [];
  const linkKeys = new Set<string>();
  const addLink = (source: string, target: string) => {
    const key = `${source}->${target}`;
    if (linkKeys.has(key)) return;
    linkKeys.add(key);
    links.push({ source, target });
  };
  graphNodes.forEach((node, index) =>
    addLink(node.id, index === 0 ? purpose.id : graphNodes[index - 1].id),
  );
  bindings.forEach((binding) => addLink(binding.id, purpose.id));
  bindingRelationEdges(model, rootByName).forEach((edge) =>
    addLink(edge.source, edge.target),
  );
  provenance.down.forEach((edge) => addLink(edge.child, edge.parent));

  const layered = layeredLayout(dagreNodes, links);
  const positioned = dagreNodes.map((node) => ({
    ...node,
    ...(layered.positions.get(node.id) ?? { x: 0, y: 0 }),
  }));
  const purposePositioned = positioned.find(
    (node) => node.id === purpose.id,
  )!;
  const graphLeft = Math.min(
    ...positioned
      .filter((node) => node.axis === "graph")
      .map((node) => node.x),
    purposePositioned.x,
  );
  purposePositioned.x = graphLeft;
  nodes.push(...positioned);
  const positionedById = new Map(
    positioned.map((node) => [node.id, node]),
  );
  distributeConnections(edges, positioned, new Set([purpose.id]));
  const bindingNodes = positioned.filter((node) => node.axis === "binding");
  const sortedBindings = [...bindingNodes].sort(
    (left, right) => left.x - right.x,
  );
  const entryY = new Map<string, number>();
  const laneY = new Map<string, number>();
  const bindingCount = sortedBindings.length;
  // Keep the heads around the edge centre, evenly spaced, rather than pinned
  // to the corners; the same rule spaces the lanes above the binding row.
  const entrySpacing =
    bindingCount > 1
      ? Math.min(
          20,
          (purposePositioned.height - 32) / (bindingCount - 1),
        )
      : 0;
  const entryCentre =
    purposePositioned.y + purposePositioned.height / 2;
  const laneSpacing = 8;
  const laneCentre = sortedBindings[0]
    ? sortedBindings[0].y - 44
    : purposePositioned.y;
  sortedBindings.forEach((binding, index) => {
    entryY.set(
      binding.id,
      entryCentre +
        (index - (bindingCount - 1) / 2) * entrySpacing,
    );
    laneY.set(
      binding.id,
      laneCentre +
        ((bindingCount - 1) / 2 - index) * laneSpacing,
    );
  });
  links.forEach((edge) => {
    const source = positionedById.get(edge.source);
    const target = positionedById.get(edge.target);
    if (!source || !target) return;
    const path =
      edge.target === purpose.id
        ? source.axis === "binding"
          ? bindingToPurposePath(
              source,
              purposePositioned,
              entryY.get(source.id) ??
                purposePositioned.y + purposePositioned.height / 2,
              laneY.get(source.id) ?? source.y - 36,
            )
          : ancestryToPurposePath(source, purposePositioned)
        : layered.paths.get(`${edge.source}->${edge.target}`);
    if (!path) return;
    edges.push({
      id: `${edge.source}->${edge.target}`,
      source: edge.source,
      target: edge.target,
      path,
      head: edgeHead(path),
    });
  });
  const axes = [
    {
      id: "graph" as const,
      text: "GRAPH",
      frame: frameFor(
        "graph",
        positioned.filter(
          (node) => node.axis === "purpose" || node.axis === "graph",
        ),
      ),
    },
    {
      id: "fulfilment" as const,
      text: "FULFILMENT",
      frame: frameFor("fulfilment", bindingNodes),
    },
    {
      id: "relation" as const,
      text: "RELATION",
      frame: frameFor(
        "relation",
        positioned.filter((node) => node.axis === "relation"),
      ),
    },
  ];
  const frames = axes.flatMap((axis) => (axis.frame ? [axis.frame] : []));
  const offset = {
    x: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.x))),
    y: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.y))),
  };
  for (const axis of axes) {
    if (!axis.frame) continue;
    labels.push({
      text: axis.text,
      x: axis.frame.x + FRAME_LABEL_INSET,
      y: axis.frame.y + FRAME_LABEL_BASELINE,
    });
  }

  const purposeNode = positioned.find((node) => node.id === purpose.id)!;
  if (!bindingNodes.length) {
    notes.push({
      text: "No binding meets these two axes.",
      x: purposeNode.x + purposeNode.width + 140,
      y: purposeNode.y + purposeNode.height / 2,
    });
  } else if (!provenance.roots.length) {
    const last = bindingNodes.reduce((lower, node) =>
      node.y + node.height > lower.y + lower.height ? node : lower,
    );
    const fulfilmentFrame = axes[1].frame;
    notes.push({
      text: "No relation is shown.",
      x: fulfilmentFrame
        ? fulfilmentFrame.x + fulfilmentFrame.width / 2
        : last.x + last.width / 2,
      y: last.y + last.height + NOTE_GAP,
    });
  }

  const nodeMaxX = Math.max(
    ...positioned.map((node) => node.x + node.width),
  );
  const nodeMaxY = Math.max(
    ...positioned.map((node) => node.y + node.height),
  );
  const noteMaxX = notes.reduce(
    (max, note) => Math.max(max, note.x + 140),
    0,
  );
  const noteMaxY = notes.reduce(
    (max, note) => Math.max(max, note.y + NOTE_HEIGHT),
    0,
  );
  const contentMaxX = Math.max(
    nodeMaxX,
    noteMaxX,
    ...frames.map((frame) => frame.x + frame.width),
  );
  const contentMaxY = Math.max(
    nodeMaxY,
    noteMaxY,
    ...frames.map((frame) => frame.y + frame.height),
  );

  return {
    nodes,
    edges,
    labels,
    notes,
    frames,
    offset,
    width: contentMaxX + offset.x,
    height: contentMaxY + offset.y,
  };
}

/**
 * A relation's, binding's or asset's constitution: the subject's purpose at
 * the top and only the declarations that produce it below. A relation subject
 * frames its provenance as RELATION; a binding frames its target record as
 * GRAPH and its relations as RELATION. An asset has no producer at all.
 */
function buildComponentsScene(model: ConstitutionModel): ConstitutionScene {
  const purpose: ConstitutionSceneNode = {
    id: "purpose",
    axis: "purpose",
    node: model.purpose,
    x: 0,
    y: 0,
    ...NODE.purpose,
  };
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: 0,
    ...NODE.graph,
  }));
  const provenance = relationProvenance(model.relation);
  const relationNodes = [...provenance.nodes.values()].map(relationNode);
  const components = [...graphNodes, ...relationNodes];
  const nodes: ConstitutionSceneNode[] = [purpose, ...components];
  const edges: ConstitutionSceneEdge[] = [];
  const notes: ConstitutionSceneNote[] = [];
  const edgeKeys = new Set<string>();
  const purposeFrameId =
    model.purpose.kind === "binding"
      ? ("fulfilment" as const)
      : model.purpose.kind === "relation" ||
          model.purpose.kind === "projection"
        ? ("relation" as const)
        : undefined;

  if (!components.length) {
    const purposeFrame = purposeFrameId
      ? frameFor(purposeFrameId, [purpose])
      : undefined;
    const frames = purposeFrame ? [purposeFrame] : [];
    const offset = {
      x: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.x))),
      y: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.y))),
    };
    const noteY = NODE.purpose.height + NOTE_GAP;
    notes.push({
      text: "No component is declared.",
      x: NODE.purpose.width / 2,
      y: noteY,
    });
    return {
      nodes,
      edges,
      labels: purposeFrame
        ? [
            {
              text: purposeFrameId === "fulfilment" ? "FULFILMENT" : "RELATION",
              x: purposeFrame.x + FRAME_LABEL_INSET,
              y: purposeFrame.y + FRAME_LABEL_BASELINE,
            },
          ]
        : [],
      notes,
      frames,
      offset,
      width:
        Math.max(
          NODE.purpose.width,
          purposeFrame ? purposeFrame.x + purposeFrame.width : 0,
          NODE.purpose.width / 2 + 140,
        ) + offset.x,
      height:
        Math.max(
          noteY + NOTE_HEIGHT,
          purposeFrame ? purposeFrame.y + purposeFrame.height : 0,
        ) + offset.y,
    };
  }

  const links: LayeredEdge[] = [];
  const addLink = (source: string, target: string) => {
    const key = `${source}->${target}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    links.push({ source, target });
  };
  graphNodes.forEach((node) => addLink(node.id, purpose.id));
  provenance.roots.forEach((id) => addLink(id, purpose.id));
  provenance.down.forEach((edge) => addLink(edge.child, edge.parent));

  const layered = layeredLayout(nodes, links);
  nodes.forEach((node) => {
    const position = layered.positions.get(node.id);
    if (position) {
      node.x = position.x;
      node.y = position.y;
    }
  });
  const positionedById = new Map(nodes.map((node) => [node.id, node]));
  const purposeSources = nodes
    .filter((node) =>
      links.some(
        (link) => link.source === node.id && link.target === purpose.id,
      ),
    )
    .sort((left, right) => left.x - right.x);
  const entrySpacing =
    purposeSources.length > 1
      ? Math.min(
          24,
          (purpose.width - 32) / (purposeSources.length - 1),
        )
      : 0;
  const entryCentre = purpose.x + purpose.width / 2;
  const entryX = new Map(
    purposeSources.map((source, index) => [
      source.id,
      entryCentre +
        (index - (purposeSources.length - 1) / 2) * entrySpacing,
    ]),
  );
  links.forEach((edge) => {
    const source = positionedById.get(edge.source);
    if (!source) return;
    const path =
      edge.target === purpose.id
        ? componentToPurposePath(
            source,
            purpose,
            entryX.get(source.id) ?? entryCentre,
          )
        : layered.paths.get(`${edge.source}->${edge.target}`);
    if (!path) return;
    edges.push({
      id: `${edge.source}->${edge.target}`,
      source: edge.source,
      target: edge.target,
      path,
      head: edgeHead(path),
    });
  });

  distributeConnections(edges, nodes, new Set([purpose.id]));
  const frames: ConstitutionSceneFrame[] = [];
  const labels: ConstitutionSceneLabel[] = [];
  const addFrame = (
    frame: ConstitutionSceneFrame | undefined,
    label: string,
  ) => {
    if (!frame) return;
    frames.push(frame);
    labels.push({
      text: label,
      x: frame.x + FRAME_LABEL_INSET,
      y: frame.y + FRAME_LABEL_BASELINE,
    });
  };

  if (purposeFrameId === "relation") {
    addFrame(
      frameFor("relation", [purpose, ...relationNodes]),
      "RELATION",
    );
  } else if (purposeFrameId === "fulfilment") {
    addFrame(frameFor("fulfilment", [purpose]), "FULFILMENT");
    addFrame(
      graphNodes.length ? frameFor("graph", graphNodes) : undefined,
      "GRAPH",
    );
    addFrame(
      relationNodes.length ? frameFor("relation", relationNodes) : undefined,
      "RELATION",
    );
  } else {
    addFrame(
      graphNodes.length ? frameFor("graph", graphNodes) : undefined,
      "GRAPH",
    );
    addFrame(
      relationNodes.length ? frameFor("relation", relationNodes) : undefined,
      "RELATION",
    );
  }

  const offset = {
    x: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.x))),
    y: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.y))),
  };

  const nodeMaxX = Math.max(
    ...nodes.map((node) => node.x + node.width),
  );
  const nodeMaxY = Math.max(
    ...nodes.map((node) => node.y + node.height),
  );
  const contentMaxX = Math.max(
    nodeMaxX,
    ...frames.map((frame) => frame.x + frame.width),
  );
  const contentMaxY = Math.max(
    nodeMaxY,
    ...frames.map((frame) => frame.y + frame.height),
  );

  return {
    nodes,
    edges,
    labels,
    notes,
    frames,
    offset,
    width: contentMaxX + offset.x,
    height: contentMaxY + offset.y,
  };
}

export function buildConstitutionScene(
  model: ConstitutionModel,
): ConstitutionScene {
  return isComponentsSubject(model.purpose.kind)
    ? buildComponentsScene(model)
    : buildRecordScene(model);
}
