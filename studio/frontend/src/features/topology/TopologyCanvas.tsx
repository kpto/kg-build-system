"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type EdgeTypes,
  type NodeTypes,
  type OnConnect,
  type OnNodeDrag,
  type Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import type { ProjectDocument } from "@/lib/ir";
import {
  buildGraph,
  categoryEndpoint,
  componentRef,
  createEdgePair,
  findCategoryEdgeForPair,
  withPosition,
  DEFAULT_FILTERS,
  type TopologyFilters,
} from "./logic";
import { CanvasProvider, type TopologyCanvasApi } from "./canvasContext";
import { VertexNodeComponent, type VertexNode } from "./VertexNode";
import { LinkEdgeComponent, type LinkEdge } from "./LinkEdge";
import { EdgeNamePopover, type EdgeDraft } from "./EdgeNamePopover";

const NODE_TYPES: NodeTypes = { vertex: VertexNodeComponent };
const EDGE_TYPES: EdgeTypes = { link: LinkEdgeComponent };

const ARROW = {
  relation: { type: MarkerType.ArrowClosed, color: "var(--color-relation)" },
  category: { type: MarkerType.ArrowClosed, color: "var(--color-edgekind)" },
  hierarchy: { type: MarkerType.ArrowClosed, color: "var(--color-category)" },
} as const;

export interface TopologyCanvasProps {
  document: ProjectDocument;
  filters: TopologyFilters;
  selectedRef: string | null;
  /** The shell's reveal gesture (problem-badge click / palette jump). */
  revealToken: number;
  /** A component id this feature asked to scroll into view (e.g. right after create). */
  revealId: string | null;
  onRevealConsumed(): void;
  onSelectRef(ref: string | null): void;
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
  onAddNode(): void;
}

/**
 * The topology canvas.
 *
 * It derives its nodes/edges from the document on every render (the document is the
 * source of truth) but owns two pieces of ephemeral state: the in-flight drag (persisted
 * once on drag end, not per frame) and the pending edge draft (the drag-to-connect
 * gesture, which hands off to the name popover). Everything else is rebuilt from props.
 */
export function TopologyCanvas(props: TopologyCanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}

function CanvasInner({
  document,
  filters,
  selectedRef,
  revealToken,
  revealId,
  onRevealConsumed,
  onSelectRef,
  apply,
  onAddNode,
}: TopologyCanvasProps) {
  const graph = useMemo(() => buildGraph(document, filters), [document, filters]);
  const rf = useReactFlow<VertexNode, LinkEdge>();

  const flowRef = useRef<HTMLDivElement | null>(null);
  const [edgeDraft, setEdgeDraft] = useState<EdgeDraft | null>(null);
  const draggingRef = useRef(false);

  // Positions and shape come from the document; the local node state only exists so the
  // library can animate a drag between frames. We re-key on the vertex set so adding or
  // removing a component remounts cleanly.
  const nodeSignature = graph.vertices.map((v) => v.id).join("|");
  const [nodes, setNodes, onNodesChange] = useNodesState<VertexNode>([]);
  const [edges, setEdges] = useEdgesState<LinkEdge>([]);

  useEffect(() => {
    if (draggingRef.current) return;
    setNodes(
      graph.vertices.map((v) => ({
        id: v.id,
        type: "vertex" as const,
        position: v.position,
        selected: v.ref === selectedRef,
        data: { component: v.component, title: v.title, subtitle: v.subtitle },
      })),
    );
    setEdges(
      graph.links.map((l) => ({
        id: l.id,
        type: "link" as const,
        source: l.source,
        target: l.target,
        selected: l.ref === selectedRef,
        markerEnd: ARROW[l.kind],
        data: { kind: l.kind, label: l.label, ref: l.ref },
      })),
    );
    // nodeSignature (not the whole graph) re-syncs on structural change; position edits
    // flow back through the document and land here on the next render after a drag stop.
  }, [nodeSignature, graph, selectedRef, setNodes, setEdges]);

  const reveal = useCallback(
    (id: string) => {
      if (!graph.refsById[id]) return;
      const vertex = graph.vertices.find((v) => v.id === id);
      const position = vertex?.position ?? rf.getNode(id)?.position;
      if (!position) return;
      void rf.setCenter(position.x + 90, position.y + 40, { zoom: 1.1, duration: 320 });
    },
    [graph, rf],
  );

  const revealRef = useCallback(
    (ref: string | null) => {
      const id = ref ? ref.replace(/^component:/, "").split(".")[0] : null;
      if (id) reveal(id);
    },
    [reveal],
  );

  // Reveal on the shell's reveal gesture (problem-badge click, palette jump).
  useEffect(() => {
    if (revealToken > 0) revealRef(selectedRef);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealToken]);

  // Reveal a component this feature just created or the search just picked. The node may
  // not be laid out on the render the create landed on, so retry until it is present.
  useEffect(() => {
    if (!revealId) return;
    let cancelled = false;
    let attempts = 0;
    const tick = () => {
      if (cancelled) return;
      if (graph.refsById[revealId]) {
        reveal(revealId);
        onRevealConsumed();
      } else if ((attempts += 1) < 12) {
        setTimeout(tick, 60);
      } else {
        onRevealConsumed();
      }
    };
    tick();
    return () => {
      cancelled = true;
    };
  }, [revealId, graph, reveal, onRevealConsumed]);

  const api = useMemo<TopologyCanvasApi>(
    () => ({
      onSelectRef,
      onNodeClick: (id) => {
        // React Flow selection is cosmetic; the document ref is the real selection.
        setNodes((current) => current.map((n) => ({ ...n, selected: n.id === id })));
      },
      reveal,
      openAddNode: onAddNode,
      revealRef,
    }),
    [onSelectRef, setNodes, reveal, onAddNode, revealRef],
  );

  const onNodeDragStop: OnNodeDrag = useCallback(
    (_event, node) => {
      draggingRef.current = false;
      const ref = componentRef(node.id);
      apply((draft) => withPosition(draft, ref, node.position));
    },
    [apply],
  );

  const onNodeDragStart = useCallback(() => {
    draggingRef.current = true;
  }, []);

  const onConnect: OnConnect = useCallback(
    (connection: Connection) => {
      const source = connection.source;
      const target = connection.target;
      if (!source || !target || source === target) return;
      // Open the name popover at the target node so the gesture stays spatial.
      const targetNode = rf.getNode(target);
      const bounds = flowRef.current?.getBoundingClientRect();
      let x = 160;
      let y = 160;
      if (targetNode && bounds) {
        const screen = rf.flowToScreenPosition(targetNode.position);
        x = Math.min(screen.x, bounds.width - 320);
        y = screen.y + 60;
      }
      setEdgeDraft({ sourceId: source, targetId: target, x, y });
    },
    [rf],
  );

  const categoryExistsFor = useCallback(
    (draft: EdgeDraft): boolean => {
      const sourceCategory = categoryEndpoint(document, draft.sourceId);
      const targetCategory = categoryEndpoint(document, draft.targetId);
      return findCategoryEdgeForPair(document, sourceCategory, targetCategory) !== null;
    },
    [document],
  );

  return (
    <CanvasProvider value={api}>
      <div ref={flowRef} className="relative min-h-0 flex-1">
        <ReactFlow<VertexNode, LinkEdge>
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          onNodeDragStart={onNodeDragStart}
          onNodeDragStop={onNodeDragStop}
          onConnect={onConnect}
          onPaneClick={() => onSelectRef(null)}
          proOptions={{ hideAttribution: true }}
          fitView
          minZoom={0.25}
          maxZoom={2}
          defaultEdgeOptions={{ type: "link" }}
          className="bg-canvas"
        >
          <Background variant={BackgroundVariant.Dots} gap={26} size={1} color="#232c3a" />
          <Controls showInteractive={false} className="!border !border-edge !bg-surface" />
        </ReactFlow>

        {edgeDraft && (
          <EdgeNamePopover
            document={document}
            draft={edgeDraft}
            categoryExists={categoryExistsFor(edgeDraft)}
            onClose={() => setEdgeDraft(null)}
            onConfirm={(input) => {
              onConfirmEdge(document, edgeDraft, input, apply, setEdgeDraft, onSelectRef);
            }}
          />
        )}
      </div>
    </CanvasProvider>
  );
}

// Isolated so the create path (the one place `createEdgePair` is wired to `apply`) reads
// in one piece; the popover hands it the predicate/label and endpoint consent.
function onConfirmEdge(
  document: ProjectDocument,
  draft: EdgeDraft,
  input: { predicate: string; label: string; createCategory: boolean },
  apply: TopologyCanvasProps["apply"],
  setEdgeDraft: (value: null) => void,
  onSelectRef: (ref: string | null) => void,
): void {
  const result = createEdgePair(document, {
    predicate: input.predicate,
    label: input.label,
    sourceId: draft.sourceId,
    targetId: draft.targetId,
    createCategoryIfMissing: input.createCategory,
  });
  setEdgeDraft(null);
  if (!result.ok) return;
  const concrete = result.concrete;
  const created = result.createdCategory;
  apply((draftDoc) => {
    let next = draftDoc;
    if (created) {
      next = { ...next, components: [...(next.components ?? []), created] };
    }
    next = { ...next, components: [...(next.components ?? []), concrete] };
    return next;
  });
  onSelectRef(componentRef(concrete.id));
}
