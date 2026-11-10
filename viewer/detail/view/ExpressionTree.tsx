"use client";

import { useId, useMemo, useState } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { resolveAssetName } from "@/lib/indexes";
import type { ViewerIndex } from "@/lib/types";
import type { ProvenanceReferences } from "@/proof/references";
import { GraphCanvas } from "@/shared/ui/GraphCanvas";
import { concepts } from "@/shared/ui/concepts";
import { theme } from "@/shared/ui/theme";
import { DetailEmptyState, DetailPanel } from "@/detail/view/DetailChrome";
import styles from "../detail.module.css";

const NODE_WIDTH = 196;
const NODE_HEIGHT = 52;
const GAP_X = 64;
const GAP_Y = 16;
const MARGIN_X = 32;
const HEADER_Y = 18;
const BODY_TOP = 40;
const BODY_BOTTOM = 28;
const FIELD_ROWS = 5;

interface TreeItem {
  concept: ConceptKind;
  label: string;
}

interface TreeEntry {
  id: string;
  concept: ConceptKind;
  label: string;
}

interface TreeColumn {
  title?: string;
  entries: TreeEntry[];
}

interface PositionedNode extends TreeEntry {
  x: number;
  y: number;
}

interface TreeLink {
  id: string;
  source: string;
  target: string;
  path: string;
}

interface TreeScene {
  nodes: PositionedNode[];
  links: TreeLink[];
  columns: Array<{ x: number; title?: string }>;
  width: number;
  height: number;
}

function entry(concept: ConceptKind, name: string): TreeEntry {
  return { id: `${concept}:${name}`, concept, label: name };
}

function dataEntries(references: ProvenanceReferences): TreeEntry[] {
  return [
    ...references.tables.map((ref) => entry("table", ref.name)),
    ...references.projections.map((ref) => entry("projection", ref.name)),
  ];
}

function fieldColumns(fields: string[]): TreeColumn[] {
  const entries = fields.map((field) => entry("field", field));
  const columnCount = Math.ceil(entries.length / FIELD_ROWS);
  const rowCount = columnCount ? Math.ceil(entries.length / columnCount) : 0;
  const columns: TreeColumn[] = [];
  for (let column = 0; column < columnCount; column += 1) {
    columns.push({
      title: column === 0 ? "Fields" : undefined,
      entries: entries.slice(column * rowCount, (column + 1) * rowCount),
    });
  }
  return columns;
}

function buildScene(
  index: ViewerIndex,
  references: ProvenanceReferences,
  item: TreeItem,
  fields: string[],
): TreeScene {
  const assets = references.assets.map((ref) => entry("asset", ref.name));
  const data = dataEntries(references);
  const itemEntry = entry(item.concept, item.label);
  const itemIsData = data.some((candidate) => candidate.id === itemEntry.id);
  const fieldTree = fieldColumns(fields);

  // A table or projection document is itself the data item: its tree starts
  // at the owning asset, names the item once and branches into its fields.
  const columns: TreeColumn[] = itemIsData
    ? [
        { title: "Source assets", entries: assets },
        {
          title: concepts[item.concept].label,
          entries: [itemEntry],
        },
        ...fieldTree,
      ]
    : [
        { title: "Source assets", entries: assets },
        { title: "Tables & projections", entries: data },
        { title: concepts[item.concept].label, entries: [itemEntry] },
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
  const nodeById = new Map<string, PositionedNode>();
  columns.forEach((column, columnIndex) => {
    const columnHeight =
      column.entries.length * NODE_HEIGHT +
      Math.max(0, column.entries.length - 1) * GAP_Y;
    const top = BODY_TOP + (bodyHeight - columnHeight) / 2;
    column.entries.forEach((treeEntry, rowIndex) => {
      const node: PositionedNode = {
        ...treeEntry,
        x: MARGIN_X + columnIndex * (NODE_WIDTH + GAP_X),
        y: top + rowIndex * (NODE_HEIGHT + GAP_Y),
      };
      nodes.push(node);
      nodeById.set(node.id, node);
    });
  });

  const links: TreeLink[] = [];
  const link = (sourceId: string, targetId: string) => {
    if (sourceId === targetId) return;
    const source = nodeById.get(sourceId);
    const target = nodeById.get(targetId);
    if (!source || !target) return;
    const sx = source.x + NODE_WIDTH;
    const sy = source.y + NODE_HEIGHT / 2;
    const tx = target.x;
    const ty = target.y + NODE_HEIGHT / 2;
    const midX = (sx + tx) / 2;
    const turn = 6;
    links.push({
      id: `${sourceId}->${targetId}`,
      source: sourceId,
      target: targetId,
      path: [
        `M ${sx} ${sy}`,
        `H ${midX - turn}`,
        `Q ${midX} ${sy} ${midX} ${sy + turn}`,
        `V ${ty - turn}`,
        `Q ${midX} ${ty} ${midX + turn} ${ty}`,
        `H ${tx}`,
      ].join(" "),
    });
  };

  if (itemIsData) {
    for (const asset of assets) link(asset.id, itemEntry.id);
  } else {
    for (const asset of assets) {
      for (const dataEntry of data) {
        if (resolveAssetName(index, dataEntry.label) === asset.label) {
          link(asset.id, dataEntry.id);
        }
      }
    }
    if (data.length) {
      for (const dataEntry of data) link(dataEntry.id, itemEntry.id);
    } else {
      for (const asset of assets) link(asset.id, itemEntry.id);
    }
  }
  for (const field of fieldTree.flatMap((column) => column.entries)) {
    link(itemEntry.id, field.id);
  }

  return {
    nodes,
    links,
    columns: columns.map((column, columnIndex) => ({
      x: MARGIN_X + columnIndex * (NODE_WIDTH + GAP_X),
      title: column.title,
    })),
    width,
    height,
  };
}

function truncated(value: string, max: number): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

/**
 * The provenance tree for one detail item. This is deliberately not a workflow
 * graph: it is a left-to-right hierarchy with column titles, flat nodes, no
 * ports and orthogonal links. It uses the shared pan/zoom canvas but its own
 * renderer and selection treatment.
 */
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
          const tint = concepts[node.concept].color;
          return (
            <g
              key={node.id}
              transform={`translate(${node.x} ${node.y})`}
              role="button"
              tabIndex={0}
              aria-pressed={selected}
              aria-label={`${concepts[node.concept].label} ${node.label}`}
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
              data-active={selected ? "true" : undefined}
            >
              <title>{`${concepts[node.concept].label} · ${node.label}`}</title>
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
                fill={tint}
                opacity={selected ? 1 : 0.8}
              />
              <text
                x={12}
                y={17}
                fill={tint}
                fontSize={7.5}
                fontWeight={600}
                letterSpacing={0.08}
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {concepts[node.concept].label.toUpperCase()}
              </text>
              <text
                x={12}
                y={36}
                fill={theme.text}
                fontSize={10}
                fontFamily="var(--font-mono)"
                pointerEvents="none"
              >
                {truncated(node.label, 26)}
              </text>
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
}: {
  index: ViewerIndex;
  references: ProvenanceReferences;
  item: TreeItem;
  fields?: string[];
}) {
  const scene = useMemo(
    () => buildScene(index, references, item, fields),
    [fields, index, item, references],
  );
  const [selectedId, setSelectedId] = useState<string>();
  const empty =
    !references.assets.length &&
    !references.tables.length &&
    !references.projections.length;

  return (
    <DetailPanel
      concept="graph"
      title="Expression tree"
      meta={`${scene.nodes.length} nodes · ${scene.links.length} links`}
    >
      {empty ? (
        <DetailEmptyState>No provenance reaches this item.</DetailEmptyState>
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
