/**
 * The constitution as one directed acyclic graph: how the subject comes to be.
 *
 * A record has purpose and one binding node per fulfilment at the top, with the
 * graph ancestry under the purpose and each binding's relation provenance under
 * the bindings. A relation, binding or asset has the subject's purpose at the
 * top and only the declarations that produce it below. The provenance is laid
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
  axis: "purpose" | "fulfilment" | "graph" | "relation";
  node: ConstitutionNode;
  /** The binding's purpose, shown instead of the node's own purpose. */
  text?: string;
  hoverable?: boolean;
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

export interface ConstitutionScene {
  nodes: ConstitutionSceneNode[];
  edges: ConstitutionSceneEdge[];
  labels: ConstitutionSceneLabel[];
  notes: ConstitutionSceneNote[];
  seam: { x: number; y1: number; y2: number } | null;
  width: number;
  height: number;
}

const NODE = {
  purpose: { width: 440, height: 96 },
  binding: { width: 300, height: 84 },
  graph: { width: 440, height: 84 },
  relation: { width: 300, height: 84 },
} as const;

const COLUMN_GAP = 60;
const BINDING_Y = 120;
const STACK_GAP = 56;
const LABEL_GAP = 24;
const LABEL_HEIGHT = 16;
const NOTE_GAP = 24;
const NOTE_HEIGHT = 24;
const EDGE_BEND = 48;

/** dagre's layered engine: top-to-bottom edges read bottom-to-top. */
const RANKDIR = "BT";
const NODE_SEP = 24;
const RANK_SEP = 48;

export function sceneNodeId(node: ConstitutionNode): string {
  return `${node.kind}:${node.name}`;
}

function verticalPath(x1: number, y1: number, x2: number, y2: number): string {
  if (Math.abs(x1 - x2) < 0.5) return `M ${x1} ${y1} L ${x2} ${y2}`;
  const bend = Math.min(EDGE_BEND, Math.abs(y1 - y2) / 2);
  return `M ${x1} ${y1} C ${x1} ${y1 - bend} ${x2} ${y2 + bend} ${x2} ${y2}`;
}

/** A binding node rises into the purpose's right edge. */
function bindingPath(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
): string {
  const bend = Math.min(EDGE_BEND, Math.abs(fromY - toY) / 2);
  return `M ${fromX} ${fromY} C ${fromX} ${fromY - bend} ${
    toX + bend
  } ${toY} ${toX} ${toY}`;
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
  /** The minimum number of ranks the edge spans. */
  minlen?: number;
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
  edges.forEach((edge) =>
    graph.setEdge(edge.source, edge.target, { minlen: edge.minlen ?? 1 }),
  );
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

/** The longest path from a relation down to its asset; the asset is 0. */
function provenanceDepth(
  down: Array<{ parent: string; child: string }>,
): (id: string) => number {
  const children = new Map<string, string[]>();
  down.forEach((edge) => {
    const list = children.get(edge.parent) ?? [];
    list.push(edge.child);
    children.set(edge.parent, list);
  });
  const cache = new Map<string, number>();
  const depth = (id: string, path = new Set<string>()): number => {
    const cached = cache.get(id);
    if (cached !== undefined) return cached;
    if (path.has(id)) return 0;
    const next = new Set(path).add(id);
    const kids = children.get(id) ?? [];
    const value = kids.length
      ? 1 + Math.max(...kids.map((child) => depth(child, next)))
      : 0;
    cache.set(id, value);
    return value;
  };
  return depth;
}

function bindingNode(binding: ConstitutionBinding): ConstitutionSceneNode {
  const node: ConstitutionNode = {
    kind: "binding",
    name: binding.name,
    label: "Fulfilment",
    meaning: binding.meaning,
  };
  return {
    id: `binding:${binding.index}`,
    axis: "fulfilment",
    node,
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
 * A record's constitution: purpose and one fulfilment per binding at the top,
 * the graph ancestry under the purpose and each binding's relation provenance
 * under the bindings.
 */
function buildRecordScene(model: ConstitutionModel): ConstitutionScene {
  const nodes: ConstitutionSceneNode[] = [];
  const edges: ConstitutionSceneEdge[] = [];
  const labels: ConstitutionSceneLabel[] = [];
  const notes: ConstitutionSceneNote[] = [];
  const edgeKeys = new Set<string>();
  const addEdge = (source: string, target: string, path: string) => {
    const id = `${source}->${target}`;
    if (edgeKeys.has(id)) return;
    edgeKeys.add(id);
    edges.push({ id, source, target, path });
  };

  const purpose: ConstitutionSceneNode = {
    id: "purpose",
    axis: "purpose",
    node: model.purpose,
    x: 0,
    y: 0,
    ...NODE.purpose,
  };

  // The record ancestry is a chain under the purpose; it is placed directly.
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node, index) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: NODE.purpose.height + STACK_GAP + index * (NODE.graph.height + STACK_GAP),
    ...NODE.graph,
  }));
  graphNodes.forEach((node, index) => {
    const target = index === 0 ? purpose : graphNodes[index - 1];
    addEdge(
      node.id,
      target.id,
      verticalPath(
        node.x + node.width / 2,
        node.y,
        target.x + target.width / 2,
        target.y + target.height,
      ),
    );
  });
  const graphBottom = graphNodes.length
    ? graphNodes[graphNodes.length - 1].y + NODE.graph.height
    : purpose.y + purpose.height;

  // The relation provenance plus the bindings form one DAG for dagre.
  const provenance = relationProvenance(model.relation);
  const bindings = model.bindings.map(bindingNode);
  const relations = [...provenance.nodes.values()].map(relationNode);
  const dagreNodes = [...bindings, ...relations];
  const rootByName = new Map<string, string>();
  provenance.roots.forEach((id) => {
    const node = provenance.nodes.get(id);
    if (node) rootByName.set(node.name, id);
  });
  const dagreEdges = [
    ...bindingRelationEdges(model, rootByName),
    ...provenance.down.map((edge) => ({
      source: edge.child,
      target: edge.parent,
    })),
  ];
  const depthOf = provenanceDepth(provenance.down);
  // Every binding answers the same purpose, so it belongs to the same rank.
  // A binding on a shallow source relation gets a longer edge to reach the
  // deepest binding rank instead of floating a row above its peers.
  const maxDepth = provenance.roots.length
    ? Math.max(...provenance.roots.map((id) => depthOf(id)))
    : 0;
  const edgesWithRank = dagreEdges.map((edge) => ({
    ...edge,
    minlen: edge.target.startsWith("binding:")
      ? Math.max(1, maxDepth + 1 - depthOf(edge.source))
      : 1,
  }));

  const regionX = NODE.purpose.width + COLUMN_GAP;
  const layered = dagreNodes.length
    ? layeredLayout(dagreNodes, edgesWithRank, { x: regionX, y: BINDING_Y })
    : undefined;

  const positioned = dagreNodes.map((node) => ({
    ...node,
    ...(layered?.positions.get(node.id) ?? { x: regionX, y: BINDING_Y }),
  }));
  nodes.push(purpose, ...positioned, ...graphNodes);

  if (layered) {
    dagreEdges.forEach((edge) => {
      const path = layered.paths.get(`${edge.source}->${edge.target}`);
      if (path) addEdge(edge.source, edge.target, path);
    });
  }
  // Each binding answers the purpose.
  positioned
    .filter((node) => node.axis === "fulfilment")
    .forEach((node) => {
      addEdge(
        node.id,
        purpose.id,
        bindingPath(
          node.x + node.width / 2,
          node.y,
          purpose.x + purpose.width,
          purpose.y + purpose.height / 2,
        ),
      );
    });

  const bindingsBottom = bindings.length
    ? BINDING_Y + NODE.binding.height
    : purpose.y + purpose.height;
  const relationBottom = layered
    ? BINDING_Y + layered.height
    : bindingsBottom;
  const regionWidth = layered ? layered.width : NODE.purpose.width;
  const regionCentre = regionX + regionWidth / 2;

  if (!model.bindings.length) {
    notes.push({
      text: "No binding meets these two axes.",
      x: regionCentre,
      y: BINDING_Y - 8,
    });
  }
  const relationLabelY = relationBottom + LABEL_GAP;
  if (!provenance.roots.length) {
    notes.push({
      text: "No relation is shown.",
      x: regionCentre,
      y: relationLabelY + 20,
    });
  }

  labels.push({
    text: "GRAPH",
    x: purpose.width / 2,
    y: graphBottom + LABEL_GAP,
  });
  labels.push({
    text: "RELATION",
    x: regionCentre,
    y: relationLabelY,
  });

  const seamX = (purpose.width + regionX) / 2;
  const seamY1 = bindingsBottom;
  const seamY2 =
    Math.max(graphBottom, relationBottom) +
    LABEL_GAP +
    (provenance.roots.length ? 8 : 40);
  const height =
    Math.max(
      bindingsBottom,
      graphBottom + LABEL_GAP + LABEL_HEIGHT,
      relationLabelY + (provenance.roots.length ? 0 : LABEL_HEIGHT + 8),
    ) + LABEL_GAP;
  const width = Math.max(purpose.width, regionX + regionWidth);

  return {
    nodes,
    edges,
    labels,
    notes,
    seam: { x: seamX, y1: seamY1, y2: seamY2 },
    width,
    height,
  };
}

/**
 * A relation's, binding's or asset's constitution: the subject's purpose at
 * the top and only the declarations that produce it below. There is no
 * fulfilment row and no graph axis. An asset has no producer at all.
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

  if (!components.length) {
    const width = NODE.purpose.width;
    const height = NODE.purpose.height + NOTE_GAP + NOTE_HEIGHT;
    notes.push({
      text: "No component is declared.",
      x: width / 2,
      y: NODE.purpose.height + NOTE_GAP,
    });
    return { nodes, edges, labels: [], notes, seam: null, width, height };
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
  links.forEach((edge) => {
    const path = layered.paths.get(`${edge.source}->${edge.target}`);
    if (!path) return;
    edges.push({
      id: `${edge.source}->${edge.target}`,
      source: edge.source,
      target: edge.target,
      path,
    });
  });

  return {
    nodes,
    edges,
    labels: [],
    notes,
    seam: null,
    width: layered.width,
    height: layered.height,
  };
}

export function buildConstitutionScene(
  model: ConstitutionModel,
): ConstitutionScene {
  return isComponentsSubject(model.purpose.kind)
    ? buildComponentsScene(model)
    : buildRecordScene(model);
}
