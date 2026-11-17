/**
 * The constitution as one directed acyclic graph.
 *
 * Purpose and fulfilment are the two top nodes; the record ancestry hangs below
 * the purpose and the relation provenance below the fulfilment. A declaration is
 * one node: a source relation or an asset shared by several consumers appears
 * once and carries one edge per consumer. Every edge points from the supply to
 * the consumer (asset → source relation → derived relation → fulfilment →
 * purpose; the graph ancestry → the purpose).
 */

import type {
  ConstitutionModel,
  ConstitutionNode,
  ConstitutionRelation,
} from "../model/constitution";

export interface ConstitutionSceneNode {
  id: string;
  axis: "purpose" | "fulfilment" | "graph" | "relation";
  node: ConstitutionNode;
  /** The fulfilment summary text, shown instead of the node purpose. */
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

export interface ConstitutionFulfilment {
  node: ConstitutionNode;
  text?: string;
  hoverable: boolean;
}

const NODE = {
  purpose: { width: 440, height: 96 },
  fulfilment: { width: 440, height: 84 },
  graph: { width: 440, height: 84 },
  relation: { width: 300, height: 84 },
} as const;

const COLUMN_GAP = 60;
const STACK_GAP = 56;
const LEVEL_COLUMNS = 2;
const LEVEL_GAP_X = 24;
const LEVEL_GAP_Y = 24;
const LABEL_GAP = 24;
const LABEL_HEIGHT = 16;
const EDGE_BEND = 48;
const EDGE_INSET = 16;

export function sceneNodeId(node: ConstitutionNode): string {
  return `${node.kind}:${node.name}`;
}

function verticalPath(x1: number, y1: number, x2: number, y2: number): string {
  if (Math.abs(x1 - x2) < 0.5) return `M ${x1} ${y1} L ${x2} ${y2}`;
  const bend = Math.min(EDGE_BEND, Math.abs(y1 - y2) / 2);
  return `M ${x1} ${y1} C ${x1} ${y1 - bend} ${x2} ${y2 + bend} ${x2} ${y2}`;
}

/** The fulfilment's top centre rises and turns into the purpose's right edge. */
function elbowPath(
  fromX: number,
  fromY: number,
  toX: number,
  toY: number,
): string {
  const radius = 12;
  return `M ${fromX} ${fromY} L ${fromX} ${toY + radius} Q ${fromX} ${toY} ${
    fromX - radius
  } ${toY} L ${toX} ${toY}`;
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

/** A shared node sits below every consumer, so every edge points one way. */
function provenanceLevels({
  nodes,
  roots,
  down,
}: RelationProvenance): Map<number, string[]> {
  const level = new Map<string, number>();
  roots.forEach((id) => level.set(id, 0));
  let changed = true;
  for (let pass = 0; pass <= nodes.size && changed; pass += 1) {
    changed = false;
    for (const edge of down) {
      const parentLevel = level.get(edge.parent);
      if (parentLevel === undefined) continue;
      const childLevel = level.get(edge.child);
      if (childLevel === undefined || childLevel < parentLevel + 1) {
        level.set(edge.child, parentLevel + 1);
        changed = true;
      }
    }
  }
  const levels = new Map<number, string[]>();
  for (const id of nodes.keys()) {
    const value = level.get(id) ?? 0;
    const ids = levels.get(value) ?? [];
    ids.push(id);
    levels.set(value, ids);
  }
  return levels;
}

export function buildConstitutionScene(
  model: ConstitutionModel,
  fulfilment: ConstitutionFulfilment,
): ConstitutionScene {
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
  const fulfilmentNode: ConstitutionSceneNode = {
    id: "fulfilment",
    axis: "fulfilment",
    node: fulfilment.node,
    text: fulfilment.text,
    hoverable: fulfilment.hoverable,
    x: NODE.purpose.width + COLUMN_GAP,
    y: 120,
    ...NODE.fulfilment,
  };
  nodes.push(purpose, fulfilmentNode);

  // The record ancestry, read from the immediate parent down to the graph
  // purpose; each node supplies the one above it.
  const graphNodes: ConstitutionSceneNode[] = model.graph.map((node, index) => ({
    id: sceneNodeId(node),
    axis: "graph",
    node,
    x: 0,
    y: NODE.purpose.height + STACK_GAP + index * (NODE.graph.height + STACK_GAP),
    ...NODE.graph,
  }));
  nodes.push(...graphNodes);
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

  // The relation provenance: every relation a binding reads, all scanned
  // relations and all assets, deduped and layered below the fulfilment.
  const provenance = relationProvenance(model.relation);
  const levels = provenanceLevels(provenance);
  const levelIds = [...levels.keys()].sort((left, right) => left - right);
  const rows = levelIds.map((level) => {
    const ids = [...(levels.get(level) ?? [])].sort((left, right) =>
      left.localeCompare(right),
    );
    const columns = Math.min(ids.length, LEVEL_COLUMNS);
    const lineCount = Math.ceil(ids.length / LEVEL_COLUMNS);
    return {
      ids,
      width:
        columns * NODE.relation.width + Math.max(0, columns - 1) * LEVEL_GAP_X,
      height:
        lineCount * NODE.relation.height +
        Math.max(0, lineCount - 1) * LEVEL_GAP_Y,
    };
  });
  const regionX = fulfilmentNode.x;
  const regionWidth = Math.max(
    NODE.fulfilment.width,
    ...rows.map((row) => row.width),
  );
  const relationTop = fulfilmentNode.y + NODE.fulfilment.height + STACK_GAP;
  const relationNodes: ConstitutionSceneNode[] = [];
  let cursorY = relationTop;
  for (const row of rows) {
    const startX = regionX + (regionWidth - row.width) / 2;
    row.ids.forEach((id, index) => {
      const node = provenance.nodes.get(id);
      if (!node) return;
      const column = index % LEVEL_COLUMNS;
      const line = Math.floor(index / LEVEL_COLUMNS);
      relationNodes.push({
        id,
        axis: "relation",
        node,
        x: startX + column * (NODE.relation.width + LEVEL_GAP_X),
        y: cursorY + line * (NODE.relation.height + LEVEL_GAP_Y),
        ...NODE.relation,
      });
    });
    cursorY += row.height + STACK_GAP;
  }
  nodes.push(...relationNodes);
  const relationBottom = rows.length ? cursorY - STACK_GAP : relationTop;

  const position = new Map(nodes.map((node) => [node.id, node]));
  // Every relation the bindings read supplies the fulfilment.
  for (const rootId of provenance.roots) {
    const root = position.get(rootId);
    if (!root) continue;
    const targetX = Math.min(
      Math.max(root.x + root.width / 2, fulfilmentNode.x + EDGE_INSET),
      fulfilmentNode.x + fulfilmentNode.width - EDGE_INSET,
    );
    addEdge(
      root.id,
      fulfilmentNode.id,
      verticalPath(
        root.x + root.width / 2,
        root.y,
        targetX,
        fulfilmentNode.y + fulfilmentNode.height,
      ),
    );
  }
  // A scanned relation or an asset supplies its consumer above it.
  for (const edge of provenance.down) {
    const child = position.get(edge.child);
    const parent = position.get(edge.parent);
    if (!child || !parent) continue;
    addEdge(
      child.id,
      parent.id,
      verticalPath(
        child.x + child.width / 2,
        child.y,
        parent.x + parent.width / 2,
        parent.y + parent.height,
      ),
    );
  }
  // The fulfilment answers the purpose.
  addEdge(
    fulfilmentNode.id,
    purpose.id,
    elbowPath(
      fulfilmentNode.x + fulfilmentNode.width / 2,
      fulfilmentNode.y,
      purpose.x + purpose.width,
      purpose.y + purpose.height / 2,
    ),
  );

  if (!provenance.roots.length) {
    notes.push({
      text: "No relation is shown.",
      x: regionX + regionWidth / 2,
      y: relationTop + 20,
    });
  }

  labels.push({
    text: "GRAPH",
    x: purpose.width / 2,
    y: graphBottom + LABEL_GAP,
  });
  labels.push({
    text: "RELATION",
    x: regionX + regionWidth / 2,
    y: relationBottom + LABEL_GAP,
  });

  const seamX = (purpose.width + fulfilmentNode.x) / 2;
  const seamY1 = fulfilmentNode.y + fulfilmentNode.height;
  const seamY2 = Math.max(graphBottom, relationBottom) + LABEL_GAP + 8;
  const height =
    Math.max(
      fulfilmentNode.y + fulfilmentNode.height,
      graphBottom + LABEL_GAP + LABEL_HEIGHT,
      relationBottom + LABEL_GAP + LABEL_HEIGHT,
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
