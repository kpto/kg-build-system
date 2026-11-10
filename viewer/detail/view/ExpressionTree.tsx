"use client";

import { useId, useMemo, useState } from "react";

import type { ConceptKind } from "@/lib/concepts";
import {
  fieldRefKey,
  logicalTypeName,
  operationName,
} from "@/lib/expressions";
import {
  relationNamesFromRowSource,
  resolveAssetName,
} from "@/lib/indexes";
import type { Expression, Ref, ViewerIndex } from "@/lib/types";
import type { ProvenanceReferences } from "@/proof/references";
import { GraphCanvas } from "@/shared/ui/GraphCanvas";
import { concepts } from "@/shared/ui/concepts";
import { theme } from "@/shared/ui/theme";
import { DetailEmptyState, DetailPanel } from "@/detail/view/DetailChrome";
import styles from "../detail.module.css";

const NODE_WIDTH = 196;
const NODE_HEIGHT = 64;
const GAP_X = 64;
const HUG_GAP_X = 12;
const GAP_Y = 16;
const MARGIN_X = 32;
const HEADER_Y = 18;
const BODY_TOP = 42;
const BODY_BOTTOM = 28;
const FIELD_ROWS = 5;

type TreeKind = ConceptKind | "expression";

interface TreeItem {
  concept: ConceptKind;
  label: string;
}

/** One output expression that the tree should explain. */
export interface ExpressionChain {
  id: string;
  target: { concept: ConceptKind; label: string; detail?: string };
  expression?: Expression;
}

interface TreeNode {
  id: string;
  kind: TreeKind;
  label: string;
  detail?: string;
  target?: boolean;
}

interface TreeEdge {
  id: string;
  source: string;
  target: string;
}

interface PositionedNode extends TreeNode {
  x: number;
  y: number;
}

interface TreeLink extends TreeEdge {
  path: string;
}

interface TreeColumn {
  x: number;
  title?: string;
}

interface TreeScene {
  nodes: PositionedNode[];
  links: TreeLink[];
  columns: TreeColumn[];
  width: number;
  height: number;
}

interface Visual {
  label: string;
  color: string;
}

function visualFor(kind: TreeKind): Visual {
  if (kind === "expression") {
    return { label: "Operator", color: theme.transform };
  }
  return concepts[kind];
}

function entry(
  kind: TreeKind,
  label: string,
  detail?: string,
  id = `${kind}:${label}`,
): TreeNode {
  return { id, kind, label, detail };
}

function projectionRelations(
  index: ViewerIndex,
  name: string,
): string[] {
  const projection = index.projectionByName.get(name);
  if (!projection) return [];
  return [
    ...new Set(
      [
        projection.row_source?.relation?.[2],
        ...relationNamesFromRowSource(projection.row_source),
      ].filter((relation): relation is string => Boolean(relation)),
    ),
  ];
}

function addTreeEdge(
  edges: Map<string, TreeEdge>,
  source: string,
  target: string,
): void {
  if (source === target) return;
  const id = `${source}->${target}`;
  if (!edges.has(id)) edges.set(id, { id, source, target });
}

/**
 * Build one DAG from the real expressions. A field leaf expands into its owner
 * table and asset; a projection column expands into its own expression before
 * feeding the parent operator. This is the expression chain, not a provenance
 * summary.
 */
function buildExpressionScene(
  index: ViewerIndex,
  chains: ExpressionChain[],
): TreeScene {
  const nodes = new Map<string, TreeNode>();
  const edges = new Map<string, TreeEdge>();
  const expandedFields = new Set<string>();

  const addNode = (node: TreeNode) => {
    if (!nodes.has(node.id)) nodes.set(node.id, node);
    return node.id;
  };
  const link = (source: string, target: string) =>
    addTreeEdge(edges, source, target);

  const addAsset = (name: string | undefined) => {
    if (!name) return undefined;
    return addNode(entry("asset", name, "source asset"));
  };
  const addTable = (name: string) =>
    addNode(entry("table", name, "relation"));

  const addSourceField = (ref: Ref): string => {
    const key = fieldRefKey(ref);
    const fieldId = addNode(
      entry(
        "field",
        key.split(".").at(-1) ?? key,
        key,
        `field:${key}`,
      ),
    );
    if (expandedFields.has(key)) return fieldId;
    expandedFields.add(key);

    const location = index.fieldsByKey.get(key);
    const owner =
      location?.ownerName ?? key.split(".")[0] ?? "field";
    const projection = index.projectionByName.get(owner);
    const relation = index.relationByName.get(owner);
    const asset = addAsset(resolveAssetName(index, owner));

    if (projection && location?.field.expression) {
      // A projection column is itself an expression. Continue through it so a
      // downstream binding shows the whole source-to-field chain.
      addExpression(
        location.field.expression,
        fieldId,
        `field:${key}`,
        "0",
      );
      return fieldId;
    }

    if (projection) {
      const projectionId = addNode(
        entry("projection", owner, "projection"),
      );
      if (asset) link(asset, projectionId);
      for (const relationName of projectionRelations(index, owner)) {
        const tableId = addTable(relationName);
        const relationAsset = addAsset(
          resolveAssetName(index, relationName),
        );
        if (relationAsset) link(relationAsset, tableId);
        link(tableId, projectionId);
      }
      link(projectionId, fieldId);
      return fieldId;
    }

    if (relation || owner) {
      const tableId = addTable(owner);
      if (asset) link(asset, tableId);
      link(tableId, fieldId);
    }
    return fieldId;
  };

  function addExpression(
    expression: Expression | undefined,
    parentId: string,
    chainKey: string,
    path: string,
  ): void {
    if (!expression) return;
    if (expression.kind === "field") {
      link(addSourceField(expression.field), parentId);
      return;
    }
    if (expression.kind === "literal") {
      const literalId = addNode(
        entry(
          "expression",
          JSON.stringify(expression.value),
          "literal",
          `literal:${chainKey}:${path}`,
        ),
      );
      link(literalId, parentId);
      return;
    }
    const operationId = addNode(
      entry(
        "expression",
        operationName(expression) ?? "operation",
        logicalTypeName(expression.logical_type),
        `op:${chainKey}:${path}`,
      ),
    );
    link(operationId, parentId);
    (expression.arguments ?? []).forEach((argument, index) =>
      addExpression(
        argument,
        operationId,
        chainKey,
        `${path}.${index}`,
      ),
    );
  }

  for (const chain of chains) {
    const targetId = addNode({
      ...entry(
        chain.target.concept,
        chain.target.label,
        chain.target.detail ?? visualFor(chain.target.concept).label,
      ),
      target: true,
    });
    if (chain.expression) {
      addExpression(chain.expression, targetId, chain.id, "0");
    }
  }

  return layoutScene([...nodes.values()], [...edges.values()]);
}

/**
 * Fallback for an item with no expression of its own, such as a source table.
 * The tree is the ownership chain: asset, table or projection, item, fields.
 */
function buildProvenanceScene(
  index: ViewerIndex,
  references: ProvenanceReferences,
  item: TreeItem,
  fields: string[],
): TreeScene {
  const assets = references.assets.map((ref) =>
    entry("asset", ref.name, "source asset"),
  );
  const data = [
    ...references.tables.map((ref) =>
      entry("table", ref.name, "relation"),
    ),
    ...references.projections.map((ref) =>
      entry("projection", ref.name, "projection"),
    ),
  ];
  const itemEntry = entry(
    item.concept,
    item.label,
    visualFor(item.concept).label,
  );
  const itemIsData = data.some(
    (candidate) => candidate.id === itemEntry.id,
  );
  const fieldEntries = fields.map((field) =>
    entry("field", field, "field"),
  );
  const fieldColumns: TreeNode[][] = [];
  const fieldColumnCount = Math.ceil(fieldEntries.length / FIELD_ROWS);
  const fieldRowCount = fieldColumnCount
    ? Math.ceil(fieldEntries.length / fieldColumnCount)
    : 0;
  for (let column = 0; column < fieldColumnCount; column += 1) {
    fieldColumns.push(
      fieldEntries.slice(
        column * fieldRowCount,
        (column + 1) * fieldRowCount,
      ),
    );
  }

  const columns: Array<{ title?: string; entries: TreeNode[] }> =
    itemIsData
      ? [
          { title: "Source assets", entries: assets },
          { title: visualFor(itemEntry.kind).label, entries: [itemEntry] },
          ...fieldColumns.map((column, columnIndex) => ({
            title: columnIndex === 0 ? "Fields" : undefined,
            entries: column,
          })),
        ]
      : [
          { title: "Source assets", entries: assets },
          { title: "Tables & projections", entries: data },
          { title: visualFor(itemEntry.kind).label, entries: [itemEntry] },
        ].filter((column) => column.entries.length);

  const maxRows = Math.max(
    1,
    ...columns.map((column) => column.entries.length),
  );
  const bodyHeight =
    maxRows * NODE_HEIGHT + Math.max(0, maxRows - 1) * GAP_Y;
  const width =
    MARGIN_X * 2 +
    columns.length * NODE_WIDTH +
    Math.max(0, columns.length - 1) * GAP_X;
  const height = BODY_TOP + bodyHeight + BODY_BOTTOM;

  const nodes: PositionedNode[] = [];
  const placed = new Map<string, PositionedNode>();
  columns.forEach((column, columnIndex) => {
    const columnHeight =
      column.entries.length * NODE_HEIGHT +
      Math.max(0, column.entries.length - 1) * GAP_Y;
    const top = BODY_TOP + (bodyHeight - columnHeight) / 2;
    column.entries.forEach((node, rowIndex) => {
      const positionedNode: PositionedNode = {
        ...node,
        x: MARGIN_X + columnIndex * (NODE_WIDTH + GAP_X),
        y: top + rowIndex * (NODE_HEIGHT + GAP_Y),
      };
      nodes.push(positionedNode);
      placed.set(node.id, positionedNode);
    });
  });

  const edges: TreeEdge[] = [];
  const add = (source: string, target: string) => {
    if (source === target) return;
    const id = `${source}->${target}`;
    if (!edges.some((edge) => edge.id === id)) {
      edges.push({ id, source, target });
    }
  };
  if (itemIsData) {
    for (const asset of assets) add(asset.id, itemEntry.id);
  } else {
    for (const asset of assets) {
      for (const dataEntry of data) {
        if (resolveAssetName(index, dataEntry.label) === asset.label) {
          add(asset.id, dataEntry.id);
        }
      }
    }
    if (data.length) {
      for (const dataEntry of data) add(dataEntry.id, itemEntry.id);
    } else {
      for (const asset of assets) add(asset.id, itemEntry.id);
    }
  }
  for (const field of fieldEntries) add(itemEntry.id, field.id);

  return {
    nodes,
    links: routedLinks(placed, edges),
    columns: columns.map((column, columnIndex) => ({
      x: MARGIN_X + columnIndex * (NODE_WIDTH + GAP_X),
      title: column.title,
    })),
    width,
    height,
  };
}

function routedLinks(
  placed: Map<string, PositionedNode>,
  edges: TreeEdge[],
): TreeLink[] {
  const links: TreeLink[] = [];
  for (const edge of edges) {
    const source = placed.get(edge.source);
    const target = placed.get(edge.target);
    if (!source || !target) continue;
    const sx = source.x + NODE_WIDTH;
    const sy = source.y + NODE_HEIGHT / 2;
    const tx = target.x;
    const ty = target.y + NODE_HEIGHT / 2;
    const midX = (sx + tx) / 2;
    const turn = 6;
    links.push({
      ...edge,
      path: [
        `M ${sx} ${sy}`,
        `H ${midX - turn}`,
        `Q ${midX} ${sy} ${midX} ${sy + turn}`,
        `V ${ty - turn}`,
        `Q ${midX} ${ty} ${midX + turn} ${ty}`,
        `H ${tx}`,
      ].join(" "),
    });
  }
  return links;
}

function layoutScene(nodes: TreeNode[], edges: TreeEdge[]): TreeScene {
  if (!nodes.length) {
    return { nodes: [], links: [], columns: [], width: 0, height: 0 };
  }
  const ids = nodes.map((node) => node.id);
  const known = new Set(ids);
  const original = new Map(ids.map((id, index) => [id, index]));
  const outgoing = new Map<string, Set<string>>();
  const predecessors = new Map<string, Set<string>>();
  const successors = new Map<string, Set<string>>();

  for (const edge of edges) {
    if (!known.has(edge.source) || !known.has(edge.target)) continue;
    if (edge.source === edge.target) continue;
    const targets = outgoing.get(edge.source) ?? new Set<string>();
    targets.add(edge.target);
    outgoing.set(edge.source, targets);
    const sources = predecessors.get(edge.target) ?? new Set<string>();
    sources.add(edge.source);
    predecessors.set(edge.target, sources);
    const next = successors.get(edge.source) ?? new Set<string>();
    next.add(edge.target);
    successors.set(edge.source, next);
  }

  const depth = new Map(ids.map((id) => [id, 0]));
  for (let pass = 0; pass < ids.length; pass += 1) {
    let changed = false;
    for (const [source, targets] of outgoing) {
      for (const target of targets) {
        const next = (depth.get(source) ?? 0) + 1;
        if (next < ids.length && next > (depth.get(target) ?? 0)) {
          depth.set(target, next);
          changed = true;
        }
      }
    }
    if (!changed) break;
  }

  const targetDepths = new Set(
    nodes
      .filter((node) => node.target)
      .map((node) => depth.get(node.id) ?? 0),
  );
  if (targetDepths.size > 1) {
    const finalTargetDepth = Math.max(...targetDepths);
    for (const node of nodes) {
      if (node.target) depth.set(node.id, finalTargetDepth);
    }
  }

  const columns = new Map<number, string[]>();
  for (const id of ids) {
    const index = depth.get(id) ?? 0;
    const column = columns.get(index) ?? [];
    column.push(id);
    columns.set(index, column);
  }
  const layerIds = [...columns.keys()].sort((left, right) => left - right);
  for (const column of columns.values()) {
    column.sort(
      (left, right) =>
        (original.get(left) ?? 0) - (original.get(right) ?? 0),
    );
  }

  const position = new Map<string, number>();
  for (const layerId of layerIds) {
    (columns.get(layerId) ?? []).forEach((id, index) =>
      position.set(id, index),
    );
  }
  const order = (
    column: string[],
    neighbours: Map<string, Set<string>>,
  ) => {
    const score = new Map<string, number>();
    for (const id of column) {
      const values = [...(neighbours.get(id) ?? [])]
        .map((neighbour) => position.get(neighbour))
        .filter((value): value is number => value !== undefined);
      if (values.length) {
        score.set(
          id,
          values.reduce((total, value) => total + value, 0) /
            values.length,
        );
      }
    }
    column.sort((left, right) => {
      const leftScore = score.get(left);
      const rightScore = score.get(right);
      if (leftScore !== undefined && rightScore !== undefined) {
        if (leftScore !== rightScore) return leftScore - rightScore;
      } else if (leftScore !== undefined) {
        return -1;
      } else if (rightScore !== undefined) {
        return 1;
      }
      return (original.get(left) ?? 0) - (original.get(right) ?? 0);
    });
  };
  for (let pass = 0; pass < 4; pass += 1) {
    const forward = pass % 2 === 0;
    const passLayers = forward
      ? layerIds.slice(1)
      : [...layerIds.slice(0, -1)].reverse();
    for (const layerId of passLayers) {
      const column = columns.get(layerId);
      if (!column) continue;
      order(column, forward ? predecessors : successors);
      column.forEach((id, index) => position.set(id, index));
    }
  }

  const nodeById = new Map(nodes.map((node) => [node.id, node]));
  const maxRows = Math.max(
    1,
    ...layerIds.map((id) => columns.get(id)?.length ?? 0),
  );
  const bodyHeight =
    maxRows * NODE_HEIGHT + Math.max(0, maxRows - 1) * GAP_Y;

  // A chain of unary operators is one visual unit: its operator columns hug
  // each other. A fan-in, a skipped layer or any non-operator boundary keeps
  // the normal gap so the crossing stays readable.
  const gapBetween = (leftId: number, rightId: number): number => {
    const left = new Set(columns.get(leftId) ?? []);
    const right = new Set(columns.get(rightId) ?? []);
    const leftNodes = [...left]
      .map((id) => nodeById.get(id))
      .filter((node): node is TreeNode => Boolean(node));
    const rightNodes = [...right]
      .map((id) => nodeById.get(id))
      .filter((node): node is TreeNode => Boolean(node));
    if (
      !leftNodes.length ||
      !rightNodes.length ||
      !leftNodes.every((node) => node.kind === "expression") ||
      !rightNodes.every((node) => node.kind === "expression")
    ) {
      return GAP_X;
    }
    const incoming = new Map<string, number>();
    for (const edge of edges) {
      if (right.has(edge.target)) {
        if (!left.has(edge.source)) return GAP_X;
        incoming.set(
          edge.target,
          (incoming.get(edge.target) ?? 0) + 1,
        );
      }
      if (left.has(edge.source) && !right.has(edge.target)) {
        return GAP_X;
      }
    }
    if (
      rightNodes.some(
        (node) => (incoming.get(node.id) ?? 0) !== 1,
      )
    ) {
      return GAP_X;
    }
    return HUG_GAP_X;
  };

  const columnX = [MARGIN_X];
  for (let index = 1; index < layerIds.length; index += 1) {
    columnX.push(
      columnX[index - 1] +
        NODE_WIDTH +
        gapBetween(layerIds[index - 1], layerIds[index]),
    );
  }
  const width =
    (columnX.at(-1) ?? MARGIN_X) + NODE_WIDTH + MARGIN_X;
  const height = BODY_TOP + bodyHeight + BODY_BOTTOM;

  const positioned: PositionedNode[] = [];
  const placed = new Map<string, PositionedNode>();
  layerIds.forEach((layerId, columnIndex) => {
    const column = columns.get(layerId) ?? [];
    const columnHeight =
      column.length * NODE_HEIGHT +
      Math.max(0, column.length - 1) * GAP_Y;
    const top = BODY_TOP + (bodyHeight - columnHeight) / 2;
    column.forEach((id, rowIndex) => {
      const node = nodeById.get(id);
      if (!node) return;
      const positionedNode: PositionedNode = {
        ...node,
        x: columnX[columnIndex],
        y: top + rowIndex * (NODE_HEIGHT + GAP_Y),
      };
      positioned.push(positionedNode);
      placed.set(id, positionedNode);
    });
  });

  const links = routedLinks(placed, edges);

  const treeColumns: TreeColumn[] = layerIds.map((layerId, index) => {
    const kinds = new Set(
      (columns.get(layerId) ?? [])
        .map((id) => nodeById.get(id)?.kind)
        .filter((kind): kind is TreeKind => Boolean(kind)),
    );
    return {
      x: columnX[index],
      title:
        kinds.size === 1
          ? visualFor([...kinds][0]).label
          : "Expression",
    };
  });

  return {
    nodes: positioned,
    links,
    columns: treeColumns,
    width,
    height,
  };
}

function truncated(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function ExpressionTreeView({
  scene,
  selectedId,
  onSelect,
}: {
  scene: TreeScene;
  selectedId?: string;
  onSelect(id: string): void;
}) {
  const markerId = `expression-arrow-${useId().replace(/:/g, "")}`;
  const incident = useMemo(() => {
    if (!selectedId) return new Set<string>();
    return new Set(
      scene.links
        .filter(
          (link) =>
            link.source === selectedId || link.target === selectedId,
        )
        .map((link) => link.id),
    );
  }, [scene.links, selectedId]);

  return (
    <>
      <defs>
        <marker
          id={markerId}
          viewBox="0 0 7 7"
          refX="6"
          refY="3.5"
          markerWidth="7"
          markerHeight="7"
          orient="auto"
        >
          <path d="M 0 0 L 7 3.5 L 0 7 z" fill={theme.edgeStrong} />
        </marker>
      </defs>
      {scene.columns.map((column) =>
        column.title ? (
          <g key={`${column.x}-${column.title}`} pointerEvents="none">
            <text
              x={column.x}
              y={HEADER_Y}
              fill={theme.faint}
              fontSize={7.5}
              fontWeight={600}
              letterSpacing={0.08}
              fontFamily="var(--font-mono)"
            >
              {column.title.toUpperCase()}
            </text>
            <line
              x1={column.x}
              x2={column.x + NODE_WIDTH}
              y1={HEADER_Y + 6}
              y2={HEADER_Y + 6}
              stroke={theme.lineSoft}
              strokeWidth={0.7}
            />
          </g>
        ) : null,
      )}
      <g data-testid="expression-edges" pointerEvents="none">
        {scene.links.map((link) => {
          const highlighted = incident.has(link.id);
          const opacity = selectedId ? (highlighted ? 0.95 : 0.16) : 0.6;
          return (
            <path
              key={link.id}
              d={link.path}
              fill="none"
              stroke={highlighted ? theme.selection : theme.edge}
              strokeWidth={highlighted ? 1.7 : 1}
              markerEnd={`url(#${markerId})`}
              opacity={opacity}
              data-testid="expression-edge"
              data-source={link.source}
              data-target={link.target}
            />
          );
        })}
      </g>
      <g data-testid="expression-nodes">
        {scene.nodes.map((node) => {
          const selected = node.id === selectedId;
          const opacity = selectedId && !selected ? 0.32 : 1;
          const visual = visualFor(node.kind);
          return (
            <g
              key={node.id}
              transform={`translate(${node.x} ${node.y})`}
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              aria-label={`${visual.label} ${node.label}`}
              onClick={(event) => {
                event.stopPropagation();
                onSelect(node.id);
              }}
              onKeyDown={(event) => {
                if (event.key !== "Enter" && event.key !== " ") return;
                event.preventDefault();
                onSelect(node.id);
              }}
              opacity={opacity}
              style={{ transition: "opacity 140ms var(--ease-instrument)" }}
              data-testid="expression-node"
              data-component={node.label}
              data-kind={node.kind}
              data-active={selected ? "true" : undefined}
            >
              <title>{`${visual.label} · ${node.label}${node.detail ? ` · ${node.detail}` : ""}`}</title>
              <rect
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={4}
                fill={theme.panel}
                stroke={selected ? theme.selection : theme.lineSoft}
                strokeWidth={selected ? 1.4 : 1}
              />
              <rect
                x={0}
                y={0}
                width={3}
                height={NODE_HEIGHT}
                rx={1.5}
                fill={visual.color}
                opacity={selected ? 1 : 0.8}
              />
              <text
                x={12}
                y={14}
                fill={visual.color}
                fontSize={7.5}
                fontWeight={600}
                letterSpacing={0.08}
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {visual.label.toUpperCase()}
              </text>
              <text
                x={12}
                y={33}
                fill={theme.text}
                fontSize={10}
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {truncated(node.label, 26)}
              </text>
              {node.detail ? (
                <text
                  x={12}
                  y={51}
                  fill={theme.faint}
                  fontSize={8}
                  fontFamily="var(--font-mono)"
                  pointerEvents="none"
                >
                  {truncated(node.detail, 30)}
                </text>
              ) : null}
            </g>
          );
        })}
      </g>
    </>
  );
}

export function ExpressionTree({
  index,
  references,
  item,
  fields = [],
  chains = [],
}: {
  index: ViewerIndex;
  references: ProvenanceReferences;
  item: TreeItem;
  fields?: string[];
  chains?: ExpressionChain[];
}) {
  const hasExpression = chains.some((chain) => chain.expression);
  const scene = useMemo(
    () =>
      hasExpression
        ? buildExpressionScene(index, chains)
        : buildProvenanceScene(index, references, item, fields),
    [chains, fields, hasExpression, index, item, references],
  );
  const [selectedId, setSelectedId] = useState<string>();
  const empty = scene.nodes.length === 0;

  return (
    <DetailPanel
      concept="graph"
      title="Expression tree"
      meta={`${scene.nodes.length} nodes · ${scene.links.length} links`}
    >
      {empty ? (
        <DetailEmptyState>No expression reaches this item.</DetailEmptyState>
      ) : (
        <GraphCanvas
          width={scene.width}
          height={scene.height}
          className={styles.expressionTree}
          minFitScale={0.5}
          testId="expression-tree"
          ariaLabel={`Expression tree from asset to ${item.label}`}
          onBackgroundClick={() => setSelectedId(undefined)}
        >
          <ExpressionTreeView
            scene={scene}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        </GraphCanvas>
      )}
    </DetailPanel>
  );
}
