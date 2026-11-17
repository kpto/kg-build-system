"use client";

import { useMemo, useState } from "react";
import { ChevronRight, Sigma } from "lucide-react";

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
import { ConceptPill } from "@/shared/ui/ConceptPill";
import { concepts } from "@/shared/ui/concepts";
import { cx, theme } from "@/shared/ui/theme";
import { DetailBand, DetailEmptyState } from "@/detail/view/DetailChrome";
import styles from "../detail.module.css";

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
}

interface TreeEdge {
  id: string;
  source: string;
  target: string;
}

interface TreeGraph {
  nodes: Map<string, TreeNode>;
  edges: TreeEdge[];
  /** The order nodes were added, used to keep sibling order stable. */
  order: Map<string, number>;
}

interface OutlineNode extends TreeNode {
  children: OutlineNode[];
}

function visualFor(kind: TreeKind): { label: string; color: string } {
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

function projectionRelations(index: ViewerIndex, name: string): string[] {
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

function addEdge(edges: Map<string, TreeEdge>, source: string, target: string) {
  if (source === target) return;
  const id = `${source}->${target}`;
  if (!edges.has(id)) edges.set(id, { id, source, target });
}

/** Build the real expression DAG. This is the same model the outline walks. */
function buildExpressionGraph(
  index: ViewerIndex,
  chains: ExpressionChain[],
): TreeGraph {
  const nodes = new Map<string, TreeNode>();
  const order = new Map<string, number>();
  const edges = new Map<string, TreeEdge>();
  const expandedFields = new Set<string>();

  const addNode = (node: TreeNode) => {
    if (!nodes.has(node.id)) {
      order.set(node.id, order.size);
      nodes.set(node.id, node);
    }
    return node.id;
  };
  const link = (source: string, target: string) =>
    addEdge(edges, source, target);
  const addAsset = (name: string | undefined) => {
    if (!name) return undefined;
    return addNode(entry("asset", name, "source asset"));
  };
  const addTable = (name: string) =>
    addNode(entry("table", name, "relation"));

  const addSourceField = (ref: Ref): string => {
    const key = fieldRefKey(ref);
    const fieldId = addNode(
      entry("field", key.split(".").at(-1) ?? key, key, `field:${key}`),
    );
    if (expandedFields.has(key)) return fieldId;
    expandedFields.add(key);

    const location = index.fieldsByKey.get(key);
    const owner = location?.ownerName ?? key.split(".")[0] ?? "field";
    const projection = index.projectionByName.get(owner);
    const relation = index.relationByName.get(owner);
    const asset = addAsset(resolveAssetName(index, owner));

    if (projection && location?.field.expression) {
      addExpression(location.field.expression, fieldId, `field:${key}`, "0");
      return fieldId;
    }

    if (projection) {
      const projectionId = addNode(entry("projection", owner, "projection"));
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
    const targetId = addNode(
      entry(
        chain.target.concept,
        chain.target.label,
        chain.target.detail ?? visualFor(chain.target.concept).label,
      ),
    );
    if (chain.expression) {
      addExpression(chain.expression, targetId, chain.id, "0");
    }
  }

  return { nodes, edges: [...edges.values()], order };
}

/** Ownership-only fallback for a source table with no expressions. */
function buildProvenanceGraph(
  index: ViewerIndex,
  references: ProvenanceReferences,
  item: TreeItem,
  fields: string[],
): TreeGraph {
  const nodes = new Map<string, TreeNode>();
  const order = new Map<string, number>();
  const edges = new Map<string, TreeEdge>();
  const addNode = (node: TreeNode) => {
    if (!nodes.has(node.id)) {
      order.set(node.id, order.size);
      nodes.set(node.id, node);
    }
    return node.id;
  };
  const link = (source: string, target: string) =>
    addEdge(edges, source, target);
  const assets = references.assets.map((ref) =>
    addNode(entry("asset", ref.name, "source asset")),
  );
  const data = [
    ...references.tables.map((ref) =>
      addNode(entry("table", ref.name, "relation")),
    ),
    ...references.projections.map((ref) =>
      addNode(entry("projection", ref.name, "projection")),
    ),
  ];
  const itemId = addNode(
    entry(item.concept, item.label, visualFor(item.concept).label),
  );
  const itemIsData = data.includes(itemId);
  if (itemIsData) {
    for (const asset of assets) link(asset, itemId);
  } else {
    for (const asset of assets) {
      for (const dataId of data) {
        const node = nodes.get(dataId);
        const assetLabel = nodes.get(asset)?.label;
        if (
          node &&
          assetLabel &&
          resolveAssetName(index, node.label) === assetLabel
        ) {
          link(asset, dataId);
        }
      }
    }
    if (data.length) {
      for (const dataId of data) link(dataId, itemId);
    } else {
      for (const asset of assets) link(asset, itemId);
    }
  }
  for (const field of fields) {
    const fieldId = addNode(entry("field", field, "field"));
    link(itemId, fieldId);
  }
  return { nodes, edges: [...edges.values()], order };
}

function outlineFromTargets(
  graph: TreeGraph,
  targetIds: string[],
): OutlineNode[] {
  const incoming = new Map<string, string[]>();
  for (const edge of graph.edges) {
    const sources = incoming.get(edge.target) ?? [];
    sources.push(edge.source);
    incoming.set(edge.target, sources);
  }
  const order = graph.order;
  const build = (id: string, visiting: Set<string>): OutlineNode => {
    const node = graph.nodes.get(id);
    if (!node) {
      return { id, kind: "graph", label: id, children: [] };
    }
    if (visiting.has(id)) {
      return { ...node, children: [] };
    }
    const next = new Set(visiting);
    next.add(id);
    const children = [...(incoming.get(id) ?? [])]
      .sort((left, right) => (order.get(left) ?? 0) - (order.get(right) ?? 0))
      .map((source) => build(source, next));
    return { ...node, children };
  };
  return targetIds.map((id) => build(id, new Set()));
}

function outlineFromRoots(graph: TreeGraph): OutlineNode[] {
  const outgoing = new Map<string, string[]>();
  const hasIncoming = new Set<string>();
  for (const edge of graph.edges) {
    const targets = outgoing.get(edge.source) ?? [];
    targets.push(edge.target);
    outgoing.set(edge.source, targets);
    hasIncoming.add(edge.target);
  }
  const order = graph.order;
  const build = (id: string, visiting: Set<string>): OutlineNode => {
    const node = graph.nodes.get(id);
    if (!node) {
      return { id, kind: "graph", label: id, children: [] };
    }
    if (visiting.has(id)) {
      return { ...node, children: [] };
    }
    const next = new Set(visiting);
    next.add(id);
    const children = [...(outgoing.get(id) ?? [])]
      .sort((left, right) => (order.get(left) ?? 0) - (order.get(right) ?? 0))
      .map((target) => build(target, next));
    return { ...node, children };
  };
  const roots = [...graph.nodes.keys()]
    .filter((id) => !hasIncoming.has(id))
    .sort((left, right) => (order.get(left) ?? 0) - (order.get(right) ?? 0));
  const selected = roots.length ? roots : [...graph.nodes.keys()];
  return selected.map((id) => build(id, new Set()));
}

function OperatorMark() {
  return (
    <Sigma
      aria-hidden
      className={styles.expressionKindIcon}
      style={{ color: theme.transform }}
    />
  );
}

function OutlineBranch({
  node,
  depth,
  root,
  collapsed,
  onToggle,
}: {
  node: OutlineNode;
  depth: number;
  root?: boolean;
  collapsed: Set<string>;
  onToggle(id: string): void;
}) {
  const open = !collapsed.has(node.id);
  const hasChildren = node.children.length > 0;
  const visual = visualFor(node.kind);
  return (
    <div className={styles.expressionBranch}>
      <div
        className={cx(
          styles.expressionRow,
          root && styles.expressionRootRow,
        )}
        data-testid="expression-node"
        data-kind={node.kind}
        data-component={node.label}
        data-root={root ? "true" : undefined}
        data-depth={depth}
        title={`${visual.label} · ${node.label}${node.detail ? ` · ${node.detail}` : ""}`}
      >
        {hasChildren ? (
          <button
            type="button"
            className={styles.expressionToggle}
            aria-expanded={open}
            aria-label={`${open ? "Collapse" : "Expand"} ${node.label}`}
            onClick={() => onToggle(node.id)}
            data-testid="expression-toggle"
          >
            <ChevronRight
              aria-hidden
              className={cx(
                styles.expressionChevron,
                open && styles.expressionChevronOpen,
              )}
            />
          </button>
        ) : (
          <span className={styles.expressionToggle} aria-hidden />
        )}
        {node.kind === "expression" ? (
          <>
            <OperatorMark />
            <span className={styles.expressionLabel}>{node.label}</span>
          </>
        ) : (
          <ConceptPill concept={node.kind} name={node.label} />
        )}
        {node.detail ? (
          <span className={styles.expressionDetail}>{node.detail}</span>
        ) : null}
      </div>
      {hasChildren && open ? (
        <div className={styles.expressionChildren}>
          {node.children.map((child, index) => (
            <OutlineBranch
              key={`${child.id}-${index}`}
              node={child}
              depth={depth + 1}
              collapsed={collapsed}
              onToggle={onToggle}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ExpressionTree({
  index,
  references,
  item,
  fields = [],
  chains = [],
  priority = "secondary",
}: {
  index: ViewerIndex;
  references: ProvenanceReferences;
  item: TreeItem;
  fields?: string[];
  chains?: ExpressionChain[];
  priority?: "primary" | "secondary";
}) {
  const hasExpression = chains.some((chain) => chain.expression);
  const graph = useMemo(
    () =>
      hasExpression
        ? buildExpressionGraph(index, chains)
        : buildProvenanceGraph(index, references, item, fields),
    [chains, fields, hasExpression, index, item, references],
  );
  const outlines = useMemo(() => {
    if (!hasExpression) return outlineFromRoots(graph);
    const targets = [...new Set(chains.map((chain) => `${chain.target.concept}:${chain.target.label}`))];
    return outlineFromTargets(graph, targets);
  }, [chains, graph, hasExpression]);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const toggle = (id: string) => {
    setCollapsed((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  return (
    <DetailBand
      concept="graph"
      priority={priority}
      title="Expression"
      question="Which fields and operations produce the value?"
      meta={`${graph.nodes.size} nodes · ${graph.edges.length} links`}
    >
      {graph.nodes.size === 0 ? (
        <DetailEmptyState>No expression reaches this item.</DetailEmptyState>
      ) : (
        <div className={styles.expressionOutline} data-testid="expression-tree">
          {outlines.map((outline, index) => (
            <div
              key={`${outline.id}-${index}`}
              className={styles.expressionRoot}
            >
              <OutlineBranch
                node={outline}
                depth={0}
                root
                collapsed={collapsed}
                onToggle={toggle}
              />
            </div>
          ))}
        </div>
      )}
    </DetailBand>
  );
}
