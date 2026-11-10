"use client";

import { useMemo, useState } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { resolveAssetName } from "@/lib/indexes";
import type { ViewerIndex } from "@/lib/types";
import type { ProvenanceReferences } from "@/proof/references";
import { concepts } from "@/shared/ui/concepts";
import { GraphCanvas } from "@/shared/ui/GraphCanvas";
import { DetailEmptyState, DetailPanel } from "@/detail/view/DetailChrome";
import {
  WorkflowGraphSceneView,
  type WorkflowGraphEdge,
  type WorkflowGraphNode,
  type WorkflowGraphScene,
} from "@/workflow/view/WorkflowGraph";
import styles from "../detail.module.css";

const WIDTH = 208;
const HEIGHT = 68;
const HEADER = 18;
const GAP_X = 56;
const GAP_Y = 14;
const MARGIN = 28;
const FIELD_ROWS = 5;

interface TreeItem {
  concept: ConceptKind;
  label: string;
}

interface TreeEntry {
  id: string;
  concept: ConceptKind;
  label: string;
  detail: string;
}

function entry(
  concept: ConceptKind,
  name: string,
  detail: string,
): TreeEntry {
  return {
    id: `${concept}:${name}`,
    concept,
    label: name,
    detail,
  };
}

function dataEntries(references: ProvenanceReferences): TreeEntry[] {
  return [
    ...references.tables.map((ref) => entry("table", ref.name, "table")),
    ...references.projections.map((ref) =>
      entry("projection", ref.name, "projection"),
    ),
  ];
}

function buildScene(
  index: ViewerIndex,
  references: ProvenanceReferences,
  item: TreeItem,
  fields: string[],
): WorkflowGraphScene {
  const assets = references.assets.map((ref) =>
    entry("asset", ref.name, "asset"),
  );
  const data = dataEntries(references);
  const itemEntry = entry(item.concept, item.label, concepts[item.concept].label);
  // A table or projection document is itself the data item. Its tree starts at
  // its asset, names the item once and terminates in its fields.
  const itemIsData = data.some((candidate) => candidate.id === itemEntry.id);
  const fieldEntries = fields.map((field) => entry("field", field, "field"));
  const fieldColumns: TreeEntry[][] = [];
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
  const columns: TreeEntry[][] = itemIsData
    ? [assets, [itemEntry], ...fieldColumns]
    : [assets, data, [itemEntry]].filter((column) => column.length);

  const maxRows = Math.max(...columns.map((column) => column.length), 1);
  const height =
    MARGIN * 2 + maxRows * HEIGHT + Math.max(0, maxRows - 1) * GAP_Y;
  const width =
    MARGIN * 2 + columns.length * WIDTH + Math.max(0, columns.length - 1) * GAP_X;
  const nodes: WorkflowGraphNode[] = [];
  const nodeById = new Map<string, WorkflowGraphNode>();
  columns.forEach((column, columnIndex) => {
    const stack = column.length * HEIGHT + Math.max(0, column.length - 1) * GAP_Y;
    const top = MARGIN + (height - MARGIN * 2 - stack) / 2;
    column.forEach((treeEntry, rowIndex) => {
      const node: WorkflowGraphNode = {
        id: treeEntry.id,
        kind: "component",
        label: treeEntry.label,
        detail: treeEntry.detail,
        meta: treeEntry.concept,
        tint: concepts[treeEntry.concept].color,
        x: MARGIN + columnIndex * (WIDTH + GAP_X),
        y: top + rowIndex * (HEIGHT + GAP_Y),
        width: WIDTH,
        height: HEIGHT,
        headerHeight: HEADER,
        socketY: HEIGHT / 2,
        dataTestId: "expression-node",
        component: treeEntry.label,
      };
      nodes.push(node);
      nodeById.set(node.id, node);
    });
  });

  const edges: WorkflowGraphEdge[] = [];
  const link = (sourceId: string, targetId: string) => {
    if (sourceId === targetId) return;
    const source = nodeById.get(sourceId);
    const target = nodeById.get(targetId);
    if (!source || !target) return;
    const sx = source.x + source.width;
    const sy = source.y + source.socketY;
    const tx = target.x;
    const ty = target.y + target.socketY;
    const dx = Math.max(36, Math.abs(tx - sx) * 0.45);
    edges.push({
      id: `${sourceId}->${targetId}`,
      source: sourceId,
      target: targetId,
      path: `M ${sx} ${sy} C ${sx + dx} ${sy}, ${tx - dx} ${ty}, ${tx} ${ty}`,
      dataTestId: "expression-edge",
    });
  };

  if (!itemIsData) {
    for (const asset of assets) {
      for (const dataEntry of data) {
        if (resolveAssetName(index, dataEntry.label) === asset.label) {
          link(asset.id, dataEntry.id);
        }
      }
    }
    for (const dataEntry of data) {
      link(dataEntry.id, itemEntry.id);
    }
  } else {
    for (const asset of assets) {
      link(asset.id, itemEntry.id);
    }
  }
  for (const field of fieldEntries) {
    link(itemEntry.id, field.id);
  }

  return { nodes, edges, width, height };
}

/**
 * The layered expression tree behind one detail item: every asset that feeds
 * the item, the tables and projections read in between, the item itself and,
 * for a data item, its fields. The scene is rendered by the shared workflow
 * graph renderer on the shared pan/zoom canvas.
 */
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
      meta={`${scene.nodes.length} nodes · ${scene.edges.length} links`}
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
          <WorkflowGraphSceneView
            scene={scene}
            selectedId={selectedId}
            onSelect={(node) => setSelectedId(node.id)}
          />
        </GraphCanvas>
      )}
    </DetailPanel>
  );
}
