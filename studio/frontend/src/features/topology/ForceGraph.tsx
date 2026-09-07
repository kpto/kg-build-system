"use client";

/**
 * The topology graph, drawn the way the framework draws its own metagraph: a force-laid
 * node-link diagram rather than a box editor.
 *
 * Reference: `kg_build_system/modules/targets/meta_graph/render.py` runs a d3 simulation
 * over the same three link kinds. Here `d3-force` computes positions (see `forceLayout`)
 * and React owns the SVG, so every shape is declarative and a document change is a
 * re-render rather than an imperative patch.
 *
 * Two things the generated artifact does not have to do and an editor must:
 *
 * - **Nothing moves while you type.** Positions are recomputed only when the vertex/link
 *   *set* changes, never when a label or a slot is edited, and the simulation is settled
 *   synchronously to a fixed result instead of animating forever.
 * - **The layout is a view; the document is the truth.** A settled position is not
 *   written back — only a drag the user performed is. A hand-placed node comes back as
 *   the seed of the next settle, so it still biases where that node lands without
 *   freezing the physics in place.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ProblemBadge, RefreshIcon } from "@/components/ui";
import type { Component, Point, ProjectDocument } from "@/lib/ir";
import { useProblemsForRef } from "@/stores/problemStore";
import {
  autoLayout,
  categoryEndpoint,
  componentById,
  componentRef,
  createEdgePair,
  findCategoryEdgeForPair,
  patchComponent,
  positionOf,
  prunePositions,
  withPosition,
  withPositions,
  type LinkView,
  type TopologyGraph,
  type VertexSize,
  type VertexView,
} from "./logic";
import { settleLayout, vertexGeometry, type VertexGeometry } from "./forceLayout";
import { EdgeNamePopover, type EdgeDraft } from "./EdgeNamePopover";

/** The layered layout packs against node cards; an edge diamond needs less room. */
const sizeFor = (vertex: VertexView): VertexSize =>
  vertex.shape === "edge" ? { width: 96, height: 96 } : { width: 216, height: 72 };

/** The arrowhead is painted this far in front of the path end, so trim that much off. */
const ARROW_ROOM = 10;
const MAX_ZOOM = 3;
const MIN_ZOOM = 0.15;

const STROKE: Record<LinkView["kind"], string> = {
  relation: "var(--color-relation)",
  category: "var(--color-edgekind)",
  hierarchy: "var(--color-category)",
};

const DASH: Record<LinkView["kind"], string | undefined> = {
  relation: undefined,
  category: "7 5",
  hierarchy: "2 6",
};

interface Transform {
  readonly x: number;
  readonly y: number;
  readonly k: number;
}

type Gesture =
  | { kind: "pan"; fromScreen: Point; origin: Transform }
  | { kind: "node"; id: string; fromGraph: Point; moved: boolean }
  | { kind: "link"; from: string; toGraph: Point };

export interface ForceGraphProps {
  document: ProjectDocument;
  graph: TopologyGraph;
  selectedRef: string | null;
  /** The shell's reveal gesture (problem-badge click / palette jump). */
  revealToken: number;
  /** A component id this feature asked to scroll into view (e.g. right after create). */
  revealId: string | null;
  onRevealConsumed(): void;
  onSelectRef(ref: string | null): void;
  apply(mutate: (draft: ProjectDocument) => ProjectDocument): void;
}

export function ForceGraph({
  document,
  graph,
  selectedRef,
  revealToken,
  revealId,
  onRevealConsumed,
  onSelectRef,
  apply,
}: ForceGraphProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ width: 960, height: 620 });
  const [transform, setTransform] = useState<Transform>({ x: 0, y: 0, k: 1 });
  const [hover, setHover] = useState<string | null>(null);
  const [dragged, setDragged] = useState<Record<string, Point>>({});
  const [edgeDraft, setEdgeDraft] = useState<EdgeDraft | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [gesture, setGesture] = useState<Gesture | null>(null);
  const framedForRef = useRef<string | null>(null);
  /** True once the user has panned or zoomed, which the auto-framing must respect. */
  const userFraming = useRef(false);
  /** Where the dragged node stood when the drag began, in graph coordinates. */
  const dragOrigin = useRef<Point | null>(null);
  /**
   * The live drag, readable synchronously at pointer-up. The `gesture` state exists to
   * paint the rubber band, but a handler firing on the same task as a `setState` would
   * still read the pre-update closure — and with a single mousemove before the release
   * that is exactly what happens, so the drop was mistaken for a click and the new
   * position was never written. Anything the terminal decision needs lives here instead.
   */
  const drag = useRef<{ id: string; moved: boolean } | null>(null);

  /**
   * The set of things drawn — deliberately not their labels or slots. Editing a
   * description changes the document and must not re-run the simulation, or typing would
   * move the graph out from under the pointer.
   */
  const structure = useMemo(
    () =>
      `${graph.vertices.map((vertex) => vertex.id).join("|")}::${graph.links
        .map((link) => `${link.id}:${link.source}>${link.target}`)
        .join("|")}`,
    [graph],
  );

  const geometry = useMemo(() => {
    const map: Record<string, VertexGeometry> = {};
    for (const vertex of graph.vertices) map[vertex.id] = vertexGeometry(vertex);
    return map;
  }, [graph]);

  const byId = useMemo(
    () => new Map(graph.vertices.map((vertex) => [vertex.id, vertex])),
    [graph],
  );

  const positions = useMemo(() => {
    // `autoLayout` is a seeding heuristic, not a second visible layout. Its column
    // invariants do not survive the force settle — measured on the demo project, seeding
    // from it leaves 4 links pointing back against 7 from no seed, which is why it is
    // here at all, and nothing downstream may assume the settled picture keeps its x
    // semantics. A position the document stores means the user placed it, so that wins.
    const seeds: Record<string, Point> = { ...autoLayout(graph.vertices, graph.links, sizeFor) };
    for (const vertex of graph.vertices) {
      const stored = positionOf(document, vertex.ref);
      if (stored) seeds[vertex.id] = stored;
    }
    const settled = settleLayout(graph.vertices, graph.links, {
      width: size.width,
      height: size.height,
      seed: seeds,
    });
    return { ...settled, ...dragged };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structure, size.width, size.height, dragged]);

  /**
   * Untangle the graph: settle from the structure alone, ignoring every hand placement,
   * and persist the result. The settled picture is written because it nearly reproduces
   * itself — re-settling from those positions drifts a node by up to ~97px on this
   * project, and up to ~140px on a denser one, since every settle restarts at full alpha
   * — so a reload shows essentially the same arrangement rather than a new one.
   */
  const resetLayout = useCallback(() => {
    const settled = settleLayout(graph.vertices, graph.links, {
      width: size.width,
      height: size.height,
    });
    setDragged({});
    apply((draft) => {
      const refs: Record<string, Point> = {};
      for (const vertex of graph.vertices) {
        const point = settled[vertex.id];
        if (point) refs[vertex.ref] = point;
      }
      return prunePositions(withPositions(draft, refs));
    });
    userFraming.current = false;
  }, [graph, size.width, size.height, apply]);

  const neighbours = useMemo(() => {
    const map: Record<string, Set<string>> = {};
    for (const vertex of graph.vertices) map[vertex.id] = new Set([vertex.id]);
    for (const link of graph.links) {
      map[link.source]?.add(link.target);
      map[link.target]?.add(link.source);
    }
    return map;
  }, [structure]); // eslint-disable-line react-hooks/exhaustive-deps

  const bounds = useCallback((): { box: { left: number; top: number; k: number }; width: number; height: number } | null => {
    const placed = graph.vertices
      .map((vertex) => positions[vertex.id])
      .filter((point): point is Point => point !== undefined);
    if (placed.length === 0 || placed.length !== graph.vertices.length) return null;
    const pad = Math.max(...graph.vertices.map((vertex) => geometry[vertex.id]?.radius ?? 24)) + 34;
    const xs = placed.map((point) => point.x);
    const ys = placed.map((point) => point.y);
    const left = Math.min(...xs) - pad;
    const top = Math.min(...ys) - pad;
    const width = Math.max(1, Math.max(...xs) + pad - left);
    const height = Math.max(1, Math.max(...ys) + pad - top);
    const k = Math.min(size.width / width, size.height / height, 1.3);
    return { box: { left, top, k }, width, height };
  }, [graph, positions, geometry, size.width, size.height]);

  const frame = useCallback(() => {
    const measured = bounds();
    if (!measured) return;
    const { left, top, k } = measured.box;
    setTransform({
      k,
      x: (size.width - measured.width * k) / 2 - left * k,
      y: (size.height - measured.height * k) / 2 - top * k,
    });
  }, [bounds, size.width, size.height]);

  // Measure the host so zoom-to-fit and the centring forces know the real box.
  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const box = entry.contentRect;
      if (box.width < 2 || box.height < 2) return;
      setSize((current) =>
        Math.abs(current.width - box.width) < 1 && Math.abs(current.height - box.height) < 1
          ? current
          : { width: box.width, height: box.height },
      );
    });
    observer.observe(host);
    return () => observer.disconnect();
  }, []);

  // Frame whenever the drawn structure changes, unless the user has taken the wheel:
  // a pan or zoom is a deliberate act and survives a later edit. Re-framing on a box
  // resize is right; overruling a user's own framing is not.
  useEffect(() => {
    if (framedForRef.current === structure) {
      // Same structure: only a host resize should move the viewport.
      frame();
      return;
    }
    framedForRef.current = structure;
    if (!userFraming.current) frame();
  }, [structure, frame]);

  const centreOn = useCallback(
    (id: string) => {
      const point = positions[id];
      if (!point) return;
      const k = Math.max(transform.k, 0.85);
      userFraming.current = true;
      setTransform({ k, x: size.width / 2 - point.x * k, y: size.height / 2 - point.y * k });
    },
    [positions, size.width, size.height, transform.k],
  );

  useEffect(() => {
    if (revealToken <= 0 || !selectedRef) return;
    const [id] = selectedRef.replace(/^component:/, "").split(".");
    if (id && positions[id]) centreOn(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [revealToken]);

  useEffect(() => {
    if (!revealId) return;
    if (positions[revealId]) {
      centreOn(revealId);
      onRevealConsumed();
    }
  }, [revealId, positions, centreOn, onRevealConsumed]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 6000);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const toGraphPoint = useCallback(
    (event: { clientX: number; clientY: number }): Point => {
      const rect = hostRef.current?.getBoundingClientRect();
      const sx = event.clientX - (rect?.left ?? 0);
      const sy = event.clientY - (rect?.top ?? 0);
      return { x: (sx - transform.x) / transform.k, y: (sy - transform.y) / transform.k };
    },
    [transform],
  );

  /** The vertex under a graph-space point, ignoring one id. Uses real drawn radii. */
  const vertexAt = useCallback(
    (point: Point, except: string): string | null => {
      let best: { id: string; distance: number } | null = null;
      for (const vertex of graph.vertices) {
        if (vertex.id === except) continue;
        const at = positions[vertex.id];
        if (!at) continue;
        const reach = (geometry[vertex.id]?.radius ?? 24) + 18;
        const distance = Math.hypot(at.x - point.x, at.y - point.y);
        if (distance <= reach && (!best || distance < best.distance)) best = { id: vertex.id, distance };
      }
      return best?.id ?? null;
    },
    [graph.vertices, positions, geometry],
  );

  /**
   * A drag that starts on a node and ends over another is a connection: node onto node
   * invents a relationship, node onto a relationship card wires that endpoint. A template
   * is refused with the reason, because the generator drops an endpoint written on one.
   */
  const proposeConnection = useCallback(
    (fromId: string, toId: string) => {
      if (fromId === toId) return;
      const from = componentById(document, fromId);
      const to = componentById(document, toId);
      if (!from || !to) return;
      const assignable = (component: Component) =>
        component.kind === "edge" && component.tier !== "template";

      if (from.kind === "node" && to.kind === "node") {
        const point = positions[toId] ?? { x: 0, y: 0 };
        const rect = hostRef.current?.getBoundingClientRect();
        setEdgeDraft({
          sourceId: fromId,
          targetId: toId,
          x: Math.min(point.x * transform.k + transform.x, (rect?.width ?? 640) - 320),
          y: point.y * transform.k + transform.y + 48,
        });
        return;
      }
      if (from.kind === "node" && to.kind === "edge") {
        if (!assignable(to)) {
          setNotice(`${to.name} is a template, and a template's endpoints reach no build`);
          return;
        }
        apply((draft) => patchComponent(draft, to.id, { source: fromId }));
        onSelectRef(componentRef(to.id));
        return;
      }
      if (from.kind === "edge" && to.kind === "node") {
        if (!assignable(from)) {
          setNotice(`${from.name} is a template, and a template's endpoints reach no build`);
          return;
        }
        apply((draft) => patchComponent(draft, from.id, { target: toId }));
        onSelectRef(componentRef(from.id));
        return;
      }
      setNotice("a relationship joins two nodes, never another relationship");
    },
    [document, positions, transform, apply, onSelectRef],
  );

  const onPointerDownNode = (event: React.PointerEvent, vertex: VertexView) => {
    event.stopPropagation();
    // Capture keeps the moves coming to us even when the pointer leaves the small shape.
    // It throws if the id is not an active pointer (a synthesised event, a lost capture),
    // and losing capture is far better than never starting the drag at all.
    try {
      hostRef.current?.setPointerCapture(event.pointerId);
    } catch {
      /* fall back to the host's own move handlers */
    }
    const at = toGraphPoint(event);
    if (event.shiftKey) {
      setGesture({ kind: "link", from: vertex.id, toGraph: at });
      return;
    }
    setGesture({ kind: "node", id: vertex.id, fromGraph: at, moved: false });
    dragOrigin.current = positions[vertex.id] ?? { x: 0, y: 0 };
    drag.current = { id: vertex.id, moved: false };
  };

  const onPointerMove = (event: React.PointerEvent) => {
    if (!gesture) return;
    if (gesture.kind === "pan") {
      setTransform({
        k: gesture.origin.k,
        x: gesture.origin.x + (event.clientX - gesture.fromScreen.x),
        y: gesture.origin.y + (event.clientY - gesture.fromScreen.y),
      });
      return;
    }
    const at = toGraphPoint(event);
    if (gesture.kind === "link") {
      setGesture({ ...gesture, toGraph: at });
      return;
    }
    const delta = { x: at.x - gesture.fromGraph.x, y: at.y - gesture.fromGraph.y };
    if (Math.hypot(delta.x, delta.y) < 4 / transform.k) return;
    setGesture({ ...gesture, moved: true });
    if (drag.current) drag.current.moved = true;
    // Measured from where the node was when the drag began, never from its current
    // position: `positions` already includes the drag offset, so re-seeding from it each
    // move would add the whole displacement again every event and the node would rocket
    // off to coordinates in the millions.
    const origin = dragOrigin.current ?? positions[gesture.id] ?? { x: 0, y: 0 };
    dragOrigin.current = origin;
    setDragged((current) => ({
      ...current,
      [gesture.id]: { x: Math.round(origin.x + delta.x), y: Math.round(origin.y + delta.y) },
    }));
  };

  const onPointerUp = (event: React.PointerEvent) => {
    if (!gesture) return;
    if (gesture.kind === "node") {
      // The ref, not `gesture`: see the `drag` declaration.
      const live = drag.current;
      const point = positions[gesture.id];
      if (live?.moved && point) {
        apply((draft) => withPosition(draft, componentRef(live.id), point));
      } else {
        onSelectRef(componentRef(gesture.id));
      }
    }
    if (gesture.kind === "link") {
      const target = vertexAt(toGraphPoint(event), gesture.from);
      if (target) proposeConnection(gesture.from, target);
    }
    dragOrigin.current = null;
    drag.current = null;
    setGesture(null);
  };

  const zoomAround = (factor: number, sx: number, sy: number) => {
    userFraming.current = true;
    setTransform((current) => {
      const k = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, current.k * factor));
      return { k, x: sx - ((sx - current.x) / current.k) * k, y: sy - ((sy - current.y) / current.k) * k };
    });
  };

  const emphasised = (hover ? neighbours[hover] : null) ?? null;
  const linkDragStart = gesture?.kind === "link" ? positions[gesture.from] : undefined;

  return (
    <div
      ref={hostRef}
      className="relative min-h-0 flex-1 touch-none overflow-hidden bg-canvas"
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={() => {
        setGesture(null);
        drag.current = null;
        dragOrigin.current = null;
      }}
      onWheel={(event) => {
        const rect = hostRef.current?.getBoundingClientRect();
        zoomAround(Math.exp(-event.deltaY * 0.0015), event.clientX - (rect?.left ?? 0), event.clientY - (rect?.top ?? 0));
      }}
      onPointerDown={(event) => {
        if ((event.target as Element).getAttribute("data-graph-pane") !== "true") return;
        try {
          hostRef.current?.setPointerCapture(event.pointerId);
        } catch {
          /* panning still works from the host's own move handler */
        }
        setGesture({
          kind: "pan",
          fromScreen: { x: event.clientX, y: event.clientY },
          origin: transform,
        });
        onSelectRef(null);
      }}
    >
      {/* `select-none` is load-bearing, not cosmetic: an SVG <text> is selectable by
          default, so dragging a node across the labels around it started a native text
          selection that fought the drag and left the canvas highlighted. Names are
          readable here and copyable in the inspector, which is not a drag surface. */}
      <svg className="absolute inset-0 h-full w-full select-none" role="img">
        <title>{`Topology graph: ${graph.vertices.length} declarations, ${graph.links.length} links`}</title>
        <defs>
          {(Object.keys(STROKE) as LinkView["kind"][]).map((kind) => (
            <marker
              key={kind}
              id={`topo-arrow-${kind}`}
              viewBox="0 -4 10 8"
              markerWidth={10}
              markerHeight={8}
              refX={10}
              refY={0}
              orient="auto"
              markerUnits="userSpaceOnUse"
            >
              <path d="M0,-4L10,0L0,4" fill={STROKE[kind]} />
            </marker>
          ))}
          <pattern id="topo-dots" width="26" height="26" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="#232c3a" />
          </pattern>
        </defs>
        <rect data-graph-pane="true" x={0} y={0} width="100%" height="100%" fill="url(#topo-dots)" />
        <g transform={`translate(${transform.x},${transform.y}) scale(${transform.k})`}>
          {graph.links.map((link) => {
            const from = positions[link.source];
            const to = positions[link.target];
            if (!from || !to) return null;
            const source = byId.get(link.source);
            const target = byId.get(link.target);
            if (!source || !target) return null;
            return (
              <GraphLink
                key={link.id}
                link={link}
                from={from}
                to={to}
                fromRadius={geometry[link.source]?.radius ?? 24}
                toRadius={geometry[link.target]?.radius ?? 24}
                dimmed={emphasised !== null && !(emphasised.has(link.source) && emphasised.has(link.target))}
                selected={link.ref === selectedRef}
                onSelect={() => onSelectRef(link.ref)}
              />
            );
          })}

          {gesture?.kind === "link" &&
            linkDragStart && (
              <line
                x1={linkDragStart.x}
                y1={linkDragStart.y}
                x2={gesture.toGraph.x}
                y2={gesture.toGraph.y}
                stroke="var(--color-info)"
                strokeWidth={2}
                strokeDasharray="5 4"
              />
            )}

          {graph.vertices.map((vertex) => (
            <GraphNode
              key={vertex.id}
              vertex={vertex}
              point={positions[vertex.id]}
              radius={geometry[vertex.id]?.radius ?? 24}
              selected={vertex.ref === selectedRef}
              dimmed={emphasised !== null && !emphasised.has(vertex.id)}
              hovered={hover === vertex.id}
              zoom={transform.k}
              onHover={setHover}
              onPointerDown={(event) => onPointerDownNode(event, vertex)}
              onSelectRef={onSelectRef}
            />
          ))}
        </g>
      </svg>

      <div className="pointer-events-none absolute inset-x-0 top-0 flex justify-center">
        {notice && (
          <span className="rounded-md border border-warn/50 bg-raised px-2.5 py-1 text-[11px] text-warn">
            {notice}
          </span>
        )}
      </div>

      <div className="absolute bottom-2 left-2 flex flex-col gap-1">
        {(["+", "−"] as const).map((glyph) => (
          <button
            key={glyph}
            type="button"
            aria-label={glyph === "+" ? "zoom in" : "zoom out"}
            title={glyph === "+" ? "zoom in" : "zoom out"}
            onClick={() => zoomAround(glyph === "+" ? 1.25 : 1 / 1.25, size.width / 2, size.height / 2)}
            className="h-6 w-6 rounded border border-edge bg-surface text-[13px] leading-none text-muted hover:text-ink"
          >
            {glyph}
          </button>
        ))}
        <button
          type="button"
          aria-label="zoom to fit"
          title="zoom to fit"
          onClick={() => {
            userFraming.current = false;
            frame();
          }}
          className="h-6 w-6 rounded border border-edge bg-surface text-[11px] leading-none text-muted hover:text-ink"
        >
          ⤢
        </button>
        <button
          type="button"
          data-testid="reset-layout-button"
          aria-label="reset layout"
          title="Untangle: re-arrange from the graph's structure, discarding hand placements, and keep the result. Undoable."
          onClick={resetLayout}
          className="mt-1 flex h-6 w-6 items-center justify-center rounded border border-edge bg-surface text-muted hover:text-ink"
        >
          <RefreshIcon size={12} />
        </button>
      </div>

      <p className="pointer-events-none absolute bottom-2 right-3 font-mono text-[10px] text-faint">
        drag to place · shift-drag onto another to connect · click a link to select it
      </p>

      {edgeDraft && (
        <EdgeNamePopover
          document={document}
          draft={edgeDraft}
          categoryExists={
            findCategoryEdgeForPair(
              document,
              categoryEndpoint(document, edgeDraft.sourceId),
              categoryEndpoint(document, edgeDraft.targetId),
            ) !== null
          }
          onClose={() => setEdgeDraft(null)}
          onConfirm={(input) => {
            const result = createEdgePair(document, {
              predicate: input.predicate,
              label: input.label,
              sourceId: edgeDraft.sourceId,
              targetId: edgeDraft.targetId,
              createCategoryIfMissing: input.createCategory,
            });
            setEdgeDraft(null);
            if (!result.ok) {
              setNotice(result.reason);
              return;
            }
            apply((draft) => {
              let next = draft;
              if (result.createdCategory) {
                next = {
                  ...next,
                  components: [...(next.components ?? []), result.createdCategory],
                };
              }
              return { ...next, components: [...(next.components ?? []), result.concrete] };
            });
            onSelectRef(componentRef(result.concrete.id));
          }}
        />
      )}
    </div>
  );
}

/** One curved link, trimmed to both shapes so the arrowhead lands on a boundary. */
function GraphLink({
  link,
  from,
  to,
  fromRadius,
  toRadius,
  dimmed,
  selected,
  onSelect,
}: {
  link: LinkView;
  from: Point;
  to: Point;
  fromRadius: number;
  toRadius: number;
  dimmed: boolean;
  selected: boolean;
  onSelect(): void;
}) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.max(1, Math.hypot(dx, dy));
  const ux = dx / distance;
  const uy = dy / distance;
  const start = { x: from.x + ux * (fromRadius + 2), y: from.y + uy * (fromRadius + 2) };
  const end = { x: to.x - ux * (toRadius + ARROW_ROOM), y: to.y - uy * (toRadius + ARROW_ROOM) };
  // A short perpendicular bow. Two links between the same pair — the in and out leg of a
  // self-joining edge category — would otherwise lie exactly on one another.
  const bow = link.role === "in" ? -16 : 16;
  const control = { x: (start.x + end.x) / 2 - uy * bow, y: (start.y + end.y) / 2 + ux * bow };
  const path = `M${start.x},${start.y} Q${control.x},${control.y} ${end.x},${end.y}`;
  const stroke = selected ? "var(--color-info)" : STROKE[link.kind];

  return (
    <g opacity={dimmed ? 0.2 : 1} style={{ transition: "opacity 120ms" }}>
      {/* A thin curve is hard to aim at, so a wide invisible path carries the click and
          selects whatever the link declares — the edge for a leg, the child for an is-a. */}
      <path
        d={path}
        stroke="transparent"
        strokeWidth={14}
        fill="none"
        style={{ cursor: "pointer" }}
        onClick={(event) => {
          event.stopPropagation();
          onSelect();
        }}
      />
      <path
        d={path}
        stroke={stroke}
        strokeWidth={selected ? 2.6 : link.kind === "relation" ? 2 : 1.4}
        strokeDasharray={DASH[link.kind]}
        fill="none"
        markerEnd={`url(#topo-arrow-${link.kind})`}
      />
    </g>
  );
}

/** One vertex: a node is a circle, a relationship is a diamond standing on its own. */
function GraphNode({
  vertex,
  point,
  radius,
  selected,
  dimmed,
  hovered,
  zoom,
  onHover,
  onPointerDown,
  onSelectRef,
}: {
  vertex: VertexView;
  point: Point | undefined;
  radius: number;
  selected: boolean;
  dimmed: boolean;
  hovered: boolean;
  zoom: number;
  onHover(id: string | null): void;
  onPointerDown(event: React.PointerEvent): void;
  onSelectRef(ref: string | null): void;
}) {
  const problems = useProblemsForRef(vertex.ref);
  if (!point) return null;
  const { component } = vertex;
  const category = component.tier === "category";
  const isEdge = vertex.shape === "edge";
  const stroke = selected
    ? "var(--color-info)"
    : isEdge
      ? category
        ? "var(--color-edgekind)"
        : "var(--color-relation)"
      : category
        ? "var(--color-category)"
        : "var(--color-node)";
  const fill = isEdge
    ? "var(--color-raised)"
    : category
      ? "var(--color-raised)"
      : "var(--color-node-soft)";
  const font = Math.max(8, 11.5 / Math.max(zoom, 0.55));
  const slots = component.properties?.length ?? 0;

  return (
    <g
      transform={`translate(${point.x},${point.y})`}
      opacity={dimmed ? 0.22 : 1}
      style={{ transition: "opacity 120ms", cursor: "grab" }}
      onPointerDown={onPointerDown}
      onPointerEnter={() => onHover(vertex.id)}
      onPointerLeave={() => onHover(null)}
      data-testid={`graph-node-${component.id}`}
      data-shape={vertex.shape}
      data-tier={component.tier}
    >
      <title>{`${component.name} · ${component.kind} ${component.tier}${
        component.label ? ` · ${component.label}` : ""
      }${component.description ? `\n${component.description}` : ""}`}</title>
      {isEdge ? (
        <path
          d={`M0,${-radius} L${radius},0 L0,${radius} L${-radius},0 Z`}
          fill={fill}
          stroke={stroke}
          strokeWidth={selected || hovered ? 2.6 : 1.8}
          strokeDasharray={category ? "5 4" : undefined}
        />
      ) : (
        <circle
          r={radius}
          fill={fill}
          stroke={stroke}
          strokeWidth={selected || hovered ? 2.6 : 1.8}
          strokeDasharray={category ? "5 4" : undefined}
        />
      )}
      {slots > 0 && (
        <text
          y={3.5}
          textAnchor="middle"
          style={{ font: `${font - 2}px ui-monospace, monospace`, fill: "var(--color-muted)" }}
        >
          {slots}
        </text>
      )}
      <text
        y={radius + font}
        textAnchor="middle"
        style={{
          font: `${font}px ui-monospace, monospace`,
          fill: hovered || selected ? "var(--color-ink)" : "var(--color-muted)",
          paintOrder: "stroke",
          stroke: "var(--color-canvas)",
          strokeWidth: 3.5,
          strokeLinejoin: "round",
        }}
      >
        {vertex.title}
      </text>
      {isEdge && component.label && (
        <text
          y={radius + font * 2 + 3}
          textAnchor="middle"
          style={{
            font: `${font - 1.5}px ui-monospace, monospace`,
            fill: stroke,
            paintOrder: "stroke",
            stroke: "var(--color-canvas)",
            strokeWidth: 3.5,
            letterSpacing: "0.05em",
          }}
        >
          {component.label}
        </text>
      )}
      <foreignObject x={radius - 10} y={-radius - 12} width={44} height={22}>
        <div className="flex justify-start">
          <ProblemBadge problems={problems} ref={vertex.ref} compact onClick={() => onSelectRef(vertex.ref)} />
        </div>
      </foreignObject>
    </g>
  );
}
