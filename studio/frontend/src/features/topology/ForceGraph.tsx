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

/** Gap left between an arrowhead's tip and the shape it points at. */
const TIP_GAP = 2;
/** Separation for links sharing the same pair of vertices. Nothing is bowed any more, so
 *  two links between one pair — a self-joining edge category's in and out leg, say — would
 *  otherwise lie exactly on top of each other pointing opposite ways. */
const PARALLEL_GAP = 14;
/** Arrowhead length and half-width, in graph units. */
const ARROW_LENGTH = 9;
const ARROW_HALF_WIDTH = 3.5;
const MAX_ZOOM = 3;
const MIN_ZOOM = 0.15;

const STROKE: Record<LinkView["kind"], string> = {
  relation: "var(--color-relation)",
  category: "var(--color-edgekind)",
  hierarchy: "var(--color-category)",
};

/**
 * Dash patterns. A declaration is dashed; an is-a is dotted with round caps on a
 * near-zero dash, which draws true round dots of the stroke's own width. A longer dash
 * (the obvious `2 6`) reads as heavy elongated ticks once the canvas is zoomed in.
 */
const DASH: Record<LinkView["kind"], string | undefined> = {
  relation: undefined,
  category: "7 5",
  hierarchy: "0.1 5",
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
  /** What the last auto-frame was computed for, so a drag never re-frames. */
  const framedFor = useRef<{
    structure: string | null;
    width: number;
    height: number;
    layout: Record<string, Point> | null;
  }>({ structure: null, width: 0, height: 0, layout: null });
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

  /**
   * Hand placements as recorded in the document, as a stable key. The settled layout
   * depends on them — that is how "reset layout" reaches the screen — but deliberately not
   * on the in-flight drag, which is overlaid afterwards.
   */
  const storedSignature = useMemo(() => {
    const parts: string[] = [];
    for (const vertex of graph.vertices) {
      const point = positionOf(document, vertex.ref);
      parts.push(point ? `${vertex.id}:${point.x},${point.y}` : `${vertex.id}:-`);
    }
    return parts.sort().join("|");
  }, [graph, document]);

  const settled = useMemo(() => {
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
    return settleLayout(graph.vertices, graph.links, {
      width: size.width,
      height: size.height,
      seed: seeds,
    });
    // Deliberately not keyed on `dragged`: the simulation must not re-run while a node is
    // being pulled, or a drag pays a full settle per mousemove.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [structure, storedSignature, size.width, size.height]);

  // A hand placement overlays the settled picture instead of feeding back into it, so
  // dragging one node cannot perturb any other.
  const positions = useMemo(() => ({ ...settled, ...dragged }), [settled, dragged]);

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
  // Frame when the drawn structure changes or the host box changes — and otherwise never.
  // This used to run on any change to `frame`'s identity, and `frame` reads the node
  // positions, so a drag re-framed the whole picture on every mousemove: the bounding box
  // now contained the dragged node in a new place, which panned and rescaled everything and
  // made every other node and edge appear to shift. A pan or zoom is deliberate, so it
  // survives both events until the user asks to fit again.
  useEffect(() => {
    const previous = framedFor.current;
    const structureChanged = previous.structure !== structure;
    const boxChanged = previous.width !== size.width || previous.height !== size.height;
    // A genuinely new settled arrangement — "reset layout", or new hand placements —
    // deserves re-framing; a drag, which only overlays, does not.
    const layoutChanged = previous.layout !== settled;
    if (!structureChanged && !boxChanged && !layoutChanged) return;
    framedFor.current = { structure, width: size.width, height: size.height, layout: settled };
    if (userFraming.current) return;
    frame();
  }, [structure, settled, size.width, size.height, frame]);

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
  const linkDragStart = gesture?.kind === "link" ? positions[gesture.from] ?? null : null;

  /**
   * Lateral offset per link. Links are drawn straight, so two of them sharing a pair of
   * vertices — the in and out leg of a self-joining relationship, or two relationships
   * between the same two nodes — would otherwise coincide exactly.
   *
   * The sign is taken against a canonical direction for the pair rather than each link's
   * own, because a link's normal is derived from its own travel direction: a leg running
   * `b → a` has the *opposite* normal to one running `a → b`, so assigning symmetric
   * offsets in each link's own frame puts both legs on the same physical side and they
   * land exactly on top of each other — which is what this originally did, at 0.15px apart.
   */
  const offsets = useMemo(() => {
    const groups = new Map<string, LinkView[]>();
    for (const link of graph.links) {
      const key = link.source < link.target
        ? `${link.source}|${link.target}`
        : `${link.target}|${link.source}`;
      const bucket = groups.get(key);
      if (bucket) bucket.push(link);
      else groups.set(key, [link]);
    }
    const out: Record<string, number> = {};
    for (const [key, group] of groups) {
      group.sort((left, right) => (left.id < right.id ? -1 : 1));
      const [canonicalSource] = key.split("|");
      group.forEach((link, index) => {
        const spread = (index - (group.length - 1) / 2) * PARALLEL_GAP;
        out[link.id] = link.source === canonicalSource ? spread : -spread;
      });
    }
    return out;
  }, [structure]); // eslint-disable-line react-hooks/exhaustive-deps

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
          {(
            [
              ...Object.keys(STROKE).map((kind) => [kind, STROKE[kind as LinkView["kind"]]]),
              ["selected", "var(--color-info)"],
            ] as const
          ).map(([kind, colour]) => (
            <marker
              key={kind}
              id={`topo-arrow-${kind}`}
              viewBox={`0 ${-ARROW_HALF_WIDTH} ${ARROW_LENGTH} ${ARROW_HALF_WIDTH * 2}`}
              markerWidth={ARROW_LENGTH}
              markerHeight={ARROW_HALF_WIDTH * 2}
              // The tip sits on the path end, so the head cannot drift back over the
              // stroke or forward off the node; sizing in user units rather than stroke
              // widths keeps emphasis from moving it.
              refX={ARROW_LENGTH}
              refY={0}
              orient="auto"
              markerUnits="userSpaceOnUse"
            >
              <path
                d={`M0,${-ARROW_HALF_WIDTH}L${ARROW_LENGTH},0L0,${ARROW_HALF_WIDTH}`}
                fill={colour}
              />
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
                fromIsDiamond={source.shape === "edge"}
                toIsDiamond={target.shape === "edge"}
                offset={offsets[link.id] ?? 0}
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

/**
 * One straight link, trimmed so its arrowhead lands on the boundary of what it points at.
 *
 * The trim is geometric rather than a fixed inset, because a fixed inset is what made the
 * heads float: a line offset to one side meets a circle on a chord, so the reachable
 * distance is √(r² − offset²) and not r; and a relationship card is a diamond, whose
 * boundary along a direction is r / (|ux| + |uy|), so treating it as a circle drove the
 * line into the flat between two vertices.
 */
function GraphLink({
  link,
  from,
  to,
  fromRadius,
  toRadius,
  fromIsDiamond,
  toIsDiamond,
  offset,
  dimmed,
  selected,
  onSelect,
}: {
  link: LinkView;
  from: Point;
  to: Point;
  fromRadius: number;
  toRadius: number;
  fromIsDiamond: boolean;
  toIsDiamond: boolean;
  offset: number;
  dimmed: boolean;
  selected: boolean;
  onSelect(): void;
}) {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.hypot(dx, dy);
  if (distance < 1) return null;
  const ux = dx / distance;
  const uy = dy / distance;
  // The unit normal, along which a group of parallel links is spread.
  const px = -uy;
  const py = ux;

  const reach = (radius: number, diamond: boolean) => {
    const shaped = diamond
      ? radius / Math.max(1e-6, Math.abs(ux) + Math.abs(uy))
      : radius;
    return Math.sqrt(Math.max(0, shaped * shaped - offset * offset));
  };

  const start = {
    x: from.x + ux * reach(fromRadius, fromIsDiamond) + px * offset,
    y: from.y + uy * reach(fromRadius, fromIsDiamond) + py * offset,
  };
  // `refX` sits on the head's tip, so the path end *is* the tip and only the visual gap is
  // trimmed here. Subtracting the head's length as well is what left it hanging short.
  const end = {
    x: to.x - ux * (reach(toRadius, toIsDiamond) + TIP_GAP) + px * offset,
    y: to.y - uy * (reach(toRadius, toIsDiamond) + TIP_GAP) + py * offset,
  };
  const path = `M${start.x},${start.y} L${end.x},${end.y}`;
  const stroke = selected ? "var(--color-info)" : STROKE[link.kind];

  return (
    <g opacity={dimmed ? 0.2 : 1} style={{ transition: "opacity 120ms" }}>
      {/* A thin straight line is hard to aim at, so a wide invisible path carries the click
          and selects whatever the link declares — the edge for a leg, the child for an is-a. */}
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
        strokeWidth={selected ? 2.4 : link.kind === "relation" ? 1.8 : 1.7}
        strokeDasharray={DASH[link.kind]}
        strokeLinecap={link.kind === "hierarchy" ? "round" : "butt"}
        fill="none"
        markerEnd={`url(#topo-arrow-${selected ? "selected" : link.kind})`}
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
