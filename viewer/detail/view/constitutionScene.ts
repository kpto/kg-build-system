/**
 * The constitution as one directed acyclic graph: how the subject comes to be.
 *
 * A record is one DAG: its graph ancestry sits on the left, its relation
 * provenance on the right, and its binding nodes between them inside the
 * fulfilment frame. A relation, binding or asset has the subject at
 * the top and only the declarations that produce it below. The graph is laid
 * out by dagre as a layered DAG, so ranks, ordering and edge routes are
 * computed rather than hand-placed. A declaration is one node: a source
 * relation or asset shared by several consumers appears once and carries one
 * edge per consumer. Every edge points from the supply to the consumer.
 */

import { graphlib, layout } from "@dagrejs/dagre";

import type {
  ConstitutionBinding,
  ConstitutionFrameId,
  ConstitutionModel,
  ConstitutionNode,
  ConstitutionRelation,
} from "../model/constitution";

export interface ConstitutionSceneNode {
  id: string;
  axis: "subject" | "binding" | "graph" | "relation";
  node: ConstitutionNode;
  /** The binding's purpose, shown instead of the node's own purpose. */
  text?: string;
  hoverable?: boolean;
  /** The pill's owner and binding identity for navigation. */
  component?: string;
  bindingIndex?: number;
  stepId?: [string, string];
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

/** One frame: the graph, relation, fulfilment or workflow group. */
export interface ConstitutionSceneFrame {
  id: ConstitutionFrameId;
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
  subject: { width: 440, height: 108 },
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
  if (node.kind === "binding" && node.bindingIndex !== undefined) {
    return `binding:${node.bindingIndex}`;
  }
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
  rankdir: "BT" | "LR" = RANKDIR,
): LayeredLayout {
  const graph = new graphlib.Graph();
  graph.setGraph({
    rankdir,
    nodesep: rankdir === "LR" ? 48 : NODE_SEP,
    ranksep: RANK_SEP,
  });
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

/** A produced subject enters the subject's bottom edge at its assigned point. */
function componentToSubjectPath(
  source: ConstitutionSceneNode,
  subject: ConstitutionSceneNode,
  entryX: number,
): string {
  return `M ${source.x + source.width / 2} ${source.y} L ${entryX} ${
    subject.y + subject.height
  }`;
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
 * points along the target's bottom edge. The subject is routed explicitly by
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

/** A subject whose constitution is its own box over its components. */
function isComponentsSubject(kind: ConstitutionNode["kind"]): boolean {
  return (
    kind === "relation" ||
    kind === "projection" ||
    kind === "binding" ||
    kind === "asset"
  );
}

/**
 * A record's constitution: one DAG whose graph ancestry and relation provenance
 * are placed by the layered layout, with no fixed side for either. The binding
 * nodes connect the two sides and are enclosed by the fulfilment frame. The
 * subject box and the bindings converge on the subject; no separator or axis
 * frame divides them.
 */
function buildRecordScene(model: ConstitutionModel): ConstitutionScene {
  const nodes: ConstitutionSceneNode[] = [];
  const edges: ConstitutionSceneEdge[] = [];
  const labels: ConstitutionSceneLabel[] = [];
  const notes: ConstitutionSceneNote[] = [];

  const subject: ConstitutionSceneNode = {
    id: "subject",
    axis: "subject",
    node: model.subject,
    ...(model.subject.kind === "step" ? { hoverable: false } : {}),
    x: 0,
    y: 0,
    ...NODE.subject,
  };
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: 0,
    ...NODE.graph,
    ...(node.collection ? { hoverable: false } : {}),
  }));
  const bindings = model.bindings.map(bindingNode);
  const provenance = relationProvenance(model.relation);
  const relations = [...provenance.nodes.values()].map(relationNode);
  const dagreNodes = [subject, ...graphNodes, ...bindings, ...relations];

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
    addLink(node.id, index === 0 ? subject.id : graphNodes[index - 1].id),
  );
  bindings.forEach((binding) => addLink(binding.id, subject.id));
  bindingRelationEdges(model, rootByName).forEach((edge) =>
    addLink(edge.source, edge.target),
  );
  provenance.down.forEach((edge) => addLink(edge.child, edge.parent));

  const layered = layeredLayout(dagreNodes, links);
  const positioned = dagreNodes.map((node) => ({
    ...node,
    ...(layered.positions.get(node.id) ?? { x: 0, y: 0 }),
  }));
  const subjectPositioned = positioned.find(
    (node) => node.id === subject.id,
  )!;
  const graphNodesPositioned = positioned.filter(
    (node) => node.axis === "graph",
  );
  if (graphNodesPositioned.length) {
    // The subject belongs to the GRAPH frame, so it sits in the ancestry
    // column. The layered layout still chooses where that column is relative
    // to the other frames.
    subjectPositioned.x = Math.min(
      ...graphNodesPositioned.map((node) => node.x),
    );
  }
  nodes.push(...positioned);
  const positionedById = new Map(
    positioned.map((node) => [node.id, node]),
  );
  links.forEach((edge) => {
    const source = positionedById.get(edge.source);
    const target = positionedById.get(edge.target);
    if (!source || !target) return;
    const path = layered.paths.get(`${edge.source}->${edge.target}`);
    if (!path) return;
    edges.push({
      id: `${edge.source}->${edge.target}`,
      source: edge.source,
      target: edge.target,
      path,
      head: edgeHead(path),
    });
  });
  distributeConnections(edges, positioned, new Set());
  const bindingNodes = positioned.filter((node) => node.axis === "binding");
  const axes = [
    {
      id: "graph" as const,
      text: "GRAPH",
      frame: frameFor(
        "graph",
        positioned.filter(
          (node) => node.axis === "subject" || node.axis === "graph",
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

  const subjectNode = positioned.find((node) => node.id === subject.id)!;
  if (!bindingNodes.length) {
    notes.push({
      text: "No binding meets these two axes.",
      x: subjectNode.x + subjectNode.width + 140,
      y: subjectNode.y + subjectNode.height / 2,
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
 * A relation's, binding's or asset's constitution: the subject at
 * the top and only the declarations that produce it below. A relation subject
 * frames its provenance as RELATION; a binding frames its target record as
 * GRAPH and its relations as RELATION. An asset has no producer at all.
 */
function buildComponentsScene(model: ConstitutionModel): ConstitutionScene {
  const subject: ConstitutionSceneNode = {
    id: "subject",
    axis: "subject",
    node: model.subject,
    ...(model.subject.kind === "step" ? { hoverable: false } : {}),
    x: 0,
    y: 0,
    ...NODE.subject,
  };
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: 0,
    ...NODE.graph,
    ...(node.collection ? { hoverable: false } : {}),
  }));
  const provenance = relationProvenance(model.relation);
  const relationNodes = [...provenance.nodes.values()].map(relationNode);
  const components = [...graphNodes, ...relationNodes];
  const nodes: ConstitutionSceneNode[] = [subject, ...components];
  const edges: ConstitutionSceneEdge[] = [];
  const notes: ConstitutionSceneNote[] = [];
  const edgeKeys = new Set<string>();
  const subjectFrameId =
    model.subject.kind === "binding"
      ? ("fulfilment" as const)
      : model.subject.kind === "relation" ||
          model.subject.kind === "projection"
        ? ("relation" as const)
        : undefined;

  if (!components.length) {
    const subjectFrame = subjectFrameId
      ? frameFor(subjectFrameId, [subject])
      : undefined;
    const frames = subjectFrame ? [subjectFrame] : [];
    const offset = {
      x: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.x))),
      y: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.y))),
    };
    const noteY = NODE.subject.height + NOTE_GAP;
    notes.push({
      text: "No component is declared.",
      x: NODE.subject.width / 2,
      y: noteY,
    });
    return {
      nodes,
      edges,
      labels: subjectFrame
        ? [
            {
              text: subjectFrameId === "fulfilment" ? "FULFILMENT" : "RELATION",
              x: subjectFrame.x + FRAME_LABEL_INSET,
              y: subjectFrame.y + FRAME_LABEL_BASELINE,
            },
          ]
        : [],
      notes,
      frames,
      offset,
      width:
        Math.max(
          NODE.subject.width,
          subjectFrame ? subjectFrame.x + subjectFrame.width : 0,
          NODE.subject.width / 2 + 140,
        ) + offset.x,
      height:
        Math.max(
          noteY + NOTE_HEIGHT,
          subjectFrame ? subjectFrame.y + subjectFrame.height : 0,
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
  graphNodes.forEach((node) => addLink(node.id, subject.id));
  provenance.roots.forEach((id) => addLink(id, subject.id));
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
  const subjectSources = nodes
    .filter((node) =>
      links.some(
        (link) => link.source === node.id && link.target === subject.id,
      ),
    )
    .sort((left, right) => left.x - right.x);
  const entrySpacing =
    subjectSources.length > 1
      ? Math.min(
          24,
          (subject.width - 32) / (subjectSources.length - 1),
        )
      : 0;
  const entryCentre = subject.x + subject.width / 2;
  const entryX = new Map(
    subjectSources.map((source, index) => [
      source.id,
      entryCentre +
        (index - (subjectSources.length - 1) / 2) * entrySpacing,
    ]),
  );
  links.forEach((edge) => {
    const source = positionedById.get(edge.source);
    if (!source) return;
    const path =
      edge.target === subject.id
        ? componentToSubjectPath(
            source,
            subject,
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

  distributeConnections(edges, nodes, new Set([subject.id]));
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

  if (subjectFrameId === "relation") {
    addFrame(
      frameFor("relation", [subject, ...relationNodes]),
      "RELATION",
    );
  } else if (subjectFrameId === "fulfilment") {
    addFrame(frameFor("fulfilment", [subject]), "FULFILMENT");
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

const FRAME_LABEL: Record<ConstitutionFrameId, string> = {
  graph: "GRAPH",
  fulfilment: "FULFILMENT",
  relation: "RELATION",
};

function frameIdForKind(kind: ConstitutionNode["kind"]): ConstitutionFrameId {
  if (kind === "binding") return "fulfilment";
  if (kind === "relation" || kind === "projection" || kind === "asset") {
    return "relation";
  }
  return "graph";
}

function frameIdForSceneNode(node: ConstitutionSceneNode): ConstitutionFrameId {
  if (node.node.frame) return node.node.frame;
  if (node.axis === "subject") return frameIdForKind(node.node.kind);
  if (node.axis === "binding") return "fulfilment";
  if (node.axis === "relation") return "relation";
  return "graph";
}

function layerAxis(frame: ConstitutionFrameId | undefined): ConstitutionSceneNode["axis"] {
  if (frame === "fulfilment") return "binding";
  if (frame === "relation") return "relation";
  return "graph";
}

/**
 * One boundary scene: the subject's subject and one level of boxes, with the
 * same box grammar, frames and layered routing as the constitution. The caller
 * decides whether the edge enters the subject (dependency) or the contribution
 * boxes (contribution).
 */
function buildBoundaryScene(
  model: ConstitutionModel,
  nodes: ConstitutionSceneNode[],
  links: LayeredEdge[],
  entry: "target" | "subject",
  note?: string,
  orientation: "vertical" | "horizontal" = "vertical",
): ConstitutionScene {
  const subject = nodes.find((node) => node.id === "subject");
  if (!subject) {
    return {
      nodes,
      edges: [],
      labels: [],
      notes: [],
      frames: [],
      offset: { x: 0, y: 0 },
      width: NODE.subject.width,
      height: NODE.subject.height,
    };
  }
  const horizontal = orientation === "horizontal";
  const layered = layeredLayout(nodes, links, { x: 0, y: 0 }, horizontal ? "LR" : "BT");
  nodes.forEach((node) => {
    const position = layered.positions.get(node.id);
    if (position) {
      node.x = position.x;
      node.y = position.y;
    }
  });
  const positionedById = new Map(nodes.map((node) => [node.id, node]));

  const subjectSources =
    entry === "subject"
      ? nodes
          .filter(
            (node) =>
              node.id !== subject.id &&
              links.some(
                (link) => link.source === node.id && link.target === subject.id,
              ),
          )
          .sort((left, right) =>
            horizontal ? left.y - right.y : left.x - right.x,
          )
      : [];
  const span = horizontal ? subject.height : subject.width;
  const spacing =
    subjectSources.length > 1
      ? Math.min(24, (span - 32) / (subjectSources.length - 1))
      : 0;
  const entryCentre = horizontal
    ? subject.y + subject.height / 2
    : subject.x + subject.width / 2;
  const entryOffset = new Map(
    subjectSources.map((source, index) => [
      source.id,
      entryCentre + (index - (subjectSources.length - 1) / 2) * spacing,
    ]),
  );

  const edges: ConstitutionSceneEdge[] = [];
  links.forEach((link) => {
    const source = positionedById.get(link.source);
    const target = positionedById.get(link.target);
    if (!source || !target) return;
    const routed = layered.paths.get(`${link.source}->${link.target}`);
    if (!routed) return;
    const path =
      target.id === subject.id
        ? horizontal
          ? moveEdgeEnd(
              routed,
              subject.x,
              entryOffset.get(source.id) ?? entryCentre,
            )
          : moveEdgeEnd(
              routed,
              entryOffset.get(source.id) ?? entryCentre,
              subject.y + subject.height,
            )
        : horizontal
          ? moveEdgeEnd(
              routed,
              target.x,
              target.y + target.height / 2,
            )
          : moveEdgeEnd(
              routed,
              target.x + target.width / 2,
              target.y + target.height,
            );
    edges.push({
      id: `${link.source}->${link.target}`,
      source: link.source,
      target: link.target,
      path,
      head: edgeHead(path),
    });
  });

  const groups = new Map<ConstitutionFrameId, ConstitutionSceneNode[]>();
  for (const node of nodes) {
    const id = frameIdForSceneNode(node);
    groups.set(id, [...(groups.get(id) ?? []), node]);
  }
  const frames: ConstitutionSceneFrame[] = [];
  const labels: ConstitutionSceneLabel[] = [];
  for (const id of ["graph", "fulfilment", "relation"] as const) {
    const members = groups.get(id);
    if (!members?.length) continue;
    const frame = frameFor(id, members);
    if (!frame) continue;
    frames.push(frame);
    labels.push({
      text: FRAME_LABEL[id],
      x: frame.x + FRAME_LABEL_INSET,
      y: frame.y + FRAME_LABEL_BASELINE,
    });
  }

  const offset = {
    x: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.x))),
    y: Math.max(0, -Math.min(0, ...frames.map((frame) => frame.y))),
  };
  const notes: ConstitutionSceneNote[] = [];
  if (note) {
    const lowest = nodes.reduce((lower, node) =>
      node.y + node.height > lower.y + lower.height ? node : lower,
    );
    notes.push({
      text: note,
      x: lowest.x + lowest.width / 2,
      y: lowest.y + lowest.height + NOTE_GAP,
    });
  }
  const nodeMaxX = Math.max(...nodes.map((node) => node.x + node.width));
  const nodeMaxY = Math.max(...nodes.map((node) => node.y + node.height));
  const noteMaxX = notes.reduce(
    (max, item) => Math.max(max, item.x + 180),
    0,
  );
  const noteMaxY = notes.reduce(
    (max, item) => Math.max(max, item.y + NOTE_HEIGHT),
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

/** One level above the subject, in the same box grammar as the constitution. */
function buildContributionScene(model: ConstitutionModel): ConstitutionScene {
  const subject: ConstitutionSceneNode = {
    id: "subject",
    axis: "subject",
    node: model.subject,
    ...(model.subject.kind === "step" ? { hoverable: false } : {}),
    x: 0,
    y: 0,
    ...NODE.subject,
  };
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: 0,
    ...NODE.graph,
    ...(node.collection ? { hoverable: false } : {}),
  }));
  const relationNodes = model.relation.map((relation) =>
    relationNode(relation.node),
  );
  const bindingNodes = model.bindings.map(bindingNode);
  const workflowNodes: ConstitutionSceneNode[] = (model.workflow ?? []).map(
    (node) => ({
      id: sceneNodeId(node),
      axis: "graph",
      node,
      x: 0,
      y: 0,
      ...NODE.relation,
      hoverable: false,
    }),
  );
  const nodes = [
    subject,
    ...graphNodes,
    ...relationNodes,
    ...bindingNodes,
    ...workflowNodes,
  ];
  const links = nodes
    .filter((node) => node.id !== subject.id)
    .map((node) => ({ source: subject.id, target: node.id }));
  return buildBoundaryScene(
    model,
    nodes,
    links,
    "target",
    nodes.length > 1
      ? undefined
      : model.note ?? "No contribution is declared.",
    "horizontal",
  );
}

/** A workflow subject: the producing or consuming steps, one level only. */
function buildWorkflowScene(model: ConstitutionModel): ConstitutionScene {
  const subject: ConstitutionSceneNode = {
    id: "subject",
    axis: "subject",
    node: model.subject,
    hoverable: false,
    x: 0,
    y: 0,
    ...NODE.subject,
  };
  const workflowNodes: ConstitutionSceneNode[] = (model.workflow ?? []).map(
    (node) => ({
      id: sceneNodeId(node),
      axis: "graph",
      node,
      x: 0,
      y: 0,
      ...NODE.relation,
      hoverable: false,
    }),
  );
  const nodes = [subject, ...workflowNodes];
  const dependency = model.direction !== "contribution";
  const links = workflowNodes.map((node) =>
    dependency
      ? { source: node.id, target: subject.id }
      : { source: subject.id, target: node.id },
  );
  return buildBoundaryScene(
    model,
    nodes,
    links,
    dependency ? "subject" : "target",
    workflowNodes.length ? undefined : model.note,
    "horizontal",
  );
}

function routeGridEdge(
  source: ConstitutionSceneNode,
  target: ConstitutionSceneNode,
): { startX: number; startY: number; endX: number; endY: number } {
  if (source.y < target.y) {
    return {
      startX: source.x + source.width / 2,
      startY: source.y + source.height,
      endX: target.x + target.width / 2,
      endY: target.y,
    };
  }
  if (source.y > target.y) {
    return {
      startX: source.x + source.width / 2,
      startY: source.y,
      endX: target.x + target.width / 2,
      endY: target.y + target.height,
    };
  }
  if (source.x < target.x) {
    return {
      startX: source.x + source.width,
      startY: source.y + source.height / 2,
      endX: target.x,
      endY: target.y + target.height / 2,
    };
  }
  return {
    startX: source.x,
    startY: source.y + source.height / 2,
    endX: target.x + target.width,
    endY: target.y + target.height / 2,
  };
}

/**
 * A collection boundary with no root: the collection's actual items and their
 * merged dependencies or contributions. One frame, real boxes.
 */
function buildSubjectSetScene(model: ConstitutionModel): ConstitutionScene {
  const layers: ConstitutionSceneNode[] = (model.layers ?? []).map((node) => ({
    id: sceneNodeId(node),
    axis: layerAxis(node.frame),
    node,
    ...(node.component ? { component: node.component } : {}),
    ...(node.bindingIndex !== undefined
      ? { bindingIndex: node.bindingIndex }
      : {}),
    ...(node.stepId ? { stepId: node.stepId } : {}),
    x: 0,
    y: 0,
    ...NODE.graph,
  }));
  const columns =
    layers.length > 40
      ? 5
      : Math.max(1, Math.min(4, Math.ceil(Math.sqrt(layers.length))));
  const gap = 32;
  layers.forEach((node, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    node.x = column * (NODE.graph.width + gap);
    node.y = row * (NODE.graph.height + gap);
  });
  const byId = new Map(layers.map((node) => [node.id, node] as const));
  const edges: ConstitutionSceneEdge[] = [];
  for (const link of model.layerEdges ?? []) {
    const source = byId.get(link.source);
    const target = byId.get(link.target);
    if (!source || !target) continue;
    const { startX, startY, endX, endY } = routeGridEdge(source, target);
    const path = `M ${startX} ${startY} L ${endX} ${endY}`;
    edges.push({
      id: `${link.source}->${link.target}`,
      source: link.source,
      target: link.target,
      path,
      head: edgeHead(path),
    });
  }
  const frameId = layers[0]
    ? frameIdForSceneNode(layers[0])
    : frameIdForKind(model.subject.kind);
  const frame = frameFor(frameId, layers);
  const frames = frame ? [frame] : [];
  const labels = frame
    ? [
        {
          text: FRAME_LABEL[frameId],
          x: frame.x + FRAME_LABEL_INSET,
          y: frame.y + FRAME_LABEL_BASELINE,
        },
      ]
    : [];
  const offset = {
    x: Math.max(0, -Math.min(0, ...frames.map((entry) => entry.x))),
    y: Math.max(0, -Math.min(0, ...frames.map((entry) => entry.y))),
  };
  const notes: ConstitutionSceneNote[] = [];
  if (model.note) {
    const lowest = layers.reduce(
      (lower, node) =>
        node.y + node.height > lower.y + lower.height ? node : lower,
      layers[0] ?? { y: 0, height: 0, x: 0, width: 0 },
    );
    notes.push({
      text: model.note,
      x: lowest.x + lowest.width / 2,
      y: lowest.y + lowest.height + NOTE_GAP,
    });
  }
  const nodeMaxX = Math.max(
    0,
    ...layers.map((node) => node.x + node.width),
  );
  const nodeMaxY = Math.max(
    0,
    ...layers.map((node) => node.y + node.height),
  );
  const contentMaxX = Math.max(
    nodeMaxX,
    ...notes.map((note) => note.x + 180),
    ...frames.map((entry) => entry.x + entry.width),
  );
  const contentMaxY = Math.max(
    nodeMaxY,
    ...notes.map((note) => note.y + NOTE_HEIGHT),
    ...frames.map((entry) => entry.y + entry.height),
  );
  return {
    nodes: layers,
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
  if (model.subjectSet) return buildSubjectSetScene(model);
  if (model.subject.kind === "step") return buildWorkflowScene(model);
  if (model.direction === "contribution") return buildContributionScene(model);
  return isComponentsSubject(model.subject.kind)
    ? buildComponentsScene(model)
    : buildRecordScene(model);
}
