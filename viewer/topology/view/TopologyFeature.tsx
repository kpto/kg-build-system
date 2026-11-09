"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import type { JSX, MouseEvent as ReactMouseEvent } from "react";
import * as d3 from "d3";

import type { DecisionStatus, Severity } from "@/lib/reviewTypes";
import type { FeatureProps, WorkbenchSelection } from "@/workbench/types";
import { cx, severityColor, theme } from "@/shared/ui/theme";
import type {
  TopologyEntity,
  TopologyGraphModel,
  TopologyLinkModel,
  TopologyNodeModel,
  TopologySelection,
  TopologyVisibleGraph,
} from "@/topology/model/TopologyGraphModel";
import {
  applyTopologyFilters,
  findTopologyEntity,
  isTopologyNode,
} from "@/topology/model/TopologyGraphModel";
import { topologyModelFor } from "@/topology/model/topologyViewModel";
import type { TopologyUiState } from "./topologyUi";
import { getTopologyUiStore, type TopologyUiStore } from "./topologyUi";

// ---------------------------------------------------------------------------
// Shared reading of the workbench contract
// ---------------------------------------------------------------------------

function topologySelection(props: FeatureProps): TopologySelection | undefined {
  const selection: WorkbenchSelection =
    props.state.functions.topology.selection;
  if (
    (selection.kind === "node" || selection.kind === "edge") &&
    selection.name
  ) {
    return { kind: selection.kind, name: selection.name };
  }
  return undefined;
}

function writeSelection(
  props: FeatureProps,
  kind: TopologySelection["kind"],
  name: string,
): void {
  props.actions.setSelection("topology", {
    activity: "topology",
    kind,
    name,
  });
}

function clearSelection(props: FeatureProps): void {
  props.actions.setSelection("topology", { activity: "topology" });
}

function useTopologyModel(props: FeatureProps): TopologyGraphModel {
  const { snapshot, index, review } = props.state;
  return useMemo(
    () => topologyModelFor(snapshot, index, review),
    [snapshot, index, review],
  );
}

function useTopologyUi(snapshot: string): readonly [TopologyUiState, TopologyUiStore] {
  const store = useMemo(() => getTopologyUiStore(snapshot), [snapshot]);
  const state = useSyncExternalStore(
    store.subscribe,
    store.getState,
    store.getState,
  );
  useEffect(() => {
    store.hydrate();
  }, [store]);
  return [state, store] as const;
}

// ---------------------------------------------------------------------------
// Shared visual vocabulary (existing theme tokens only)
// ---------------------------------------------------------------------------

const DECISION_COLOR: Record<DecisionStatus, string> = {
  accepted: theme.asset,
  proposed: theme.medium,
  open: theme.medium,
  rejected: theme.critical,
  waived: theme.info,
};

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
  info: "info",
};

function statusColor(entity: TopologyEntity): string | undefined {
  if (entity.findings.worst) return severityColor[entity.findings.worst];
  if (entity.decisionStatus) return DECISION_COLOR[entity.decisionStatus];
  return undefined;
}

function nodeRadius(node: TopologyNodeModel): number {
  return Math.max(4.5, Math.min(18, 4 + Math.sqrt(Math.max(1, node.degree)) * 1.9));
}

function nodeFill(node: TopologyNodeModel): string {
  return node.abstract ? theme.asset : theme.source;
}

function pointerPosition(
  container: HTMLElement | null,
  event: ReactMouseEvent,
): { x: number; y: number } | undefined {
  const rect = container?.getBoundingClientRect();
  if (!rect) return undefined;
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function formatStatus(entity: TopologyEntity): string {
  const parts: string[] = [];
  if (entity.hasSemantics) parts.push("semantics");
  if (entity.findings.total) {
    parts.push(
      `${entity.findings.total} finding${entity.findings.total === 1 ? "" : "s"}`,
    );
  }
  if (entity.decisionStatus) parts.push(`decision ${entity.decisionStatus}`);
  return parts.length ? parts.join(" · ") : "no semantics, finding or decision";
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function FilterButton({
  pressed,
  onClick,
  children,
  count,
  title,
}: {
  pressed: boolean;
  onClick: () => void;
  children: React.ReactNode;
  count?: number;
  title?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      title={title}
      className={cx(
        "inline-flex min-h-6 items-center gap-1 border px-1.5 py-0.5 font-mono text-[10px] transition-colors",
        pressed
          ? "border-accent/70 bg-accent/15 text-accent-strong"
          : "border-line-soft bg-panel-soft/40 text-muted hover:border-line-strong hover:text-text",
      )}
    >
      <span>{children}</span>
      {count !== undefined ? (
        <span className="text-[9px] text-faint tabular-nums">{count}</span>
      ) : null}
    </button>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <p className="text-[9px] tracking-[0.08em] text-faint uppercase">{label}</p>
      <div className="flex flex-wrap gap-1">{children}</div>
    </div>
  );
}

function LegendRow({
  color,
  label,
  count,
  dashed,
}: {
  color: string;
  label: string;
  count?: number;
  dashed?: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span
        aria-hidden
        className={cx(
          "size-2 shrink-0 rounded-full",
          dashed ? "border border-dashed bg-transparent" : "",
        )}
        style={dashed ? { borderColor: color } : { backgroundColor: color }}
      />
      <span className="min-w-0 flex-1 truncate text-[10px] text-muted">
        {label}
      </span>
      {count !== undefined ? (
        <span className="font-mono text-[9px] text-faint tabular-nums">{count}</span>
      ) : null}
    </div>
  );
}

export function TopologySidebar(props: FeatureProps): JSX.Element {
  const model = useTopologyModel(props);
  const [ui, store] = useTopologyUi(props.state.snapshot.name);
  const visible = useMemo(
    () => applyTopologyFilters(model, ui.filters),
    [model, ui.filters],
  );
  const filters = ui.filters;
  const counts = model.filters.counts;

  const patchFilters = (
    patch: Partial<Omit<typeof filters, "kinds">> & {
      kinds?: Partial<typeof filters.kinds>;
    },
  ) => {
    store.setFilters({
      ...filters,
      ...patch,
      kinds: { ...filters.kinds, ...(patch.kinds ?? {}) },
    });
  };

  const relationLinks = visible.links.filter((link) => link.kind === "edge").length;
  const visibleFindings = [...visible.nodes, ...visible.links.filter((link) => link.kind === "edge")].filter(
    (entity) => entity.findings.total > 0,
  ).length;

  return (
    <div className="flex h-full min-h-0 flex-col bg-panel">
      <header className="border-b border-line-soft px-3 py-2">
        <p className="text-[10px] text-muted">
          {visible.nodes.length} visible · {relationLinks} relations
          {visibleFindings ? ` · ${visibleFindings} with findings` : ""}
        </p>
        <p className="mt-0.5 font-mono text-[9px] text-faint tabular-nums">
          {model.stats.nodes} nodes · {model.stats.edgeLinks} edges ·{" "}
          {model.stats.semantics} with semantics
        </p>
      </header>

      <div className="thin-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-2">
        <section className="space-y-2" aria-label="Topology filters">
          <FilterGroup label="Kind">
            <FilterButton
              pressed={filters.kinds.node}
              onClick={() => {
                patchFilters({ kinds: { node: !filters.kinds.node } });
                store.requestFit();
              }}
              count={counts.kinds.node}
              title="Show or hide topology node components"
            >
              Nodes
            </FilterButton>
            <FilterButton
              pressed={filters.kinds.edge}
              onClick={() => {
                patchFilters({ kinds: { edge: !filters.kinds.edge } });
                store.requestFit();
              }}
              count={counts.kinds.edge}
              title="Show or hide topology edge components as relation links"
            >
              Relations
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Abstract">
            <FilterButton
              pressed={filters.abstract === "all"}
              onClick={() => patchFilters({ abstract: "all" })}
              count={counts.abstract.all}
            >
              All
            </FilterButton>
            <FilterButton
              pressed={filters.abstract === "concrete"}
              onClick={() => patchFilters({ abstract: "concrete" })}
              count={counts.abstract.concrete}
            >
              Concrete
            </FilterButton>
            <FilterButton
              pressed={filters.abstract === "abstract"}
              onClick={() => patchFilters({ abstract: "abstract" })}
              count={counts.abstract.abstract}
            >
              Abstract
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Semantics">
            <FilterButton
              pressed={filters.semantics === "all"}
              onClick={() => patchFilters({ semantics: "all" })}
              count={counts.semantics.all}
            >
              All
            </FilterButton>
            <FilterButton
              pressed={filters.semantics === "present"}
              onClick={() => patchFilters({ semantics: "present" })}
              count={counts.semantics.present}
            >
              Present
            </FilterButton>
            <FilterButton
              pressed={filters.semantics === "missing"}
              onClick={() => patchFilters({ semantics: "missing" })}
              count={counts.semantics.missing}
            >
              Missing
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Findings">
            <FilterButton
              pressed={filters.findings === "all"}
              onClick={() => patchFilters({ findings: "all" })}
              count={counts.findings.all}
            >
              All
            </FilterButton>
            <FilterButton
              pressed={filters.findings === "with"}
              onClick={() => patchFilters({ findings: "with" })}
              count={counts.findings.with}
            >
              With
            </FilterButton>
            <FilterButton
              pressed={filters.findings === "without"}
              onClick={() => patchFilters({ findings: "without" })}
              count={counts.findings.without}
            >
              Clean
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Decision">
            <FilterButton
              pressed={filters.decision === "all"}
              onClick={() => patchFilters({ decision: "all" })}
              count={counts.decision.all}
            >
              All
            </FilterButton>
            <FilterButton
              pressed={filters.decision === "none"}
              onClick={() => patchFilters({ decision: "none" })}
              count={counts.decision.none}
            >
              None
            </FilterButton>
            <FilterButton
              pressed={filters.decision === "accepted"}
              onClick={() => patchFilters({ decision: "accepted" })}
              count={counts.decision.accepted}
            >
              Accepted
            </FilterButton>
            <FilterButton
              pressed={filters.decision === "open"}
              onClick={() => patchFilters({ decision: "open" })}
              count={counts.decision.open}
            >
              Open
            </FilterButton>
            <FilterButton
              pressed={filters.decision === "proposed"}
              onClick={() => patchFilters({ decision: "proposed" })}
              count={counts.decision.proposed}
            >
              Proposed
            </FilterButton>
            <FilterButton
              pressed={filters.decision === "rejected"}
              onClick={() => patchFilters({ decision: "rejected" })}
              count={counts.decision.rejected}
            >
              Rejected
            </FilterButton>
          </FilterGroup>
        </section>

        <section className="space-y-1.5 border-t border-line-soft pt-2" aria-label="Topology legend">
          <p className="text-[9px] tracking-[0.08em] text-faint uppercase">Legend</p>
          <LegendRow
            color={theme.source}
            label="Concrete node"
            count={model.stats.nodes - model.stats.abstractNodes}
          />
          <LegendRow
            color={theme.asset}
            label="Abstract category"
            count={model.stats.abstractNodes}
            dashed
          />
          <LegendRow color={theme.edge} label="Relation edge" count={model.stats.edgeLinks} />
          <LegendRow
            color={theme.lineStrong}
            label="Category containment"
            count={model.stats.containmentLinks}
            dashed
          />
          <LegendRow color={theme.critical} label="Finding" />
          <LegendRow color={theme.asset} label="Decision accepted" />
          <LegendRow color={theme.medium} label="Decision open / proposed" />
          <LegendRow color={theme.critical} label="Decision rejected" />
          <p className="pt-1 text-[9px] leading-relaxed text-faint">
            Ring = audit severity, then decision. Orange ring = selection.
          </p>
        </section>

        <section className="space-y-1.5 border-t border-line-soft pt-2" aria-label="Topology layout">
          <p className="text-[9px] tracking-[0.08em] text-faint uppercase">Layout</p>
          <div className="flex flex-wrap gap-1">
            <button
              type="button"
              onClick={() => store.requestFit()}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[10px] text-muted hover:border-line-strong hover:text-text"
              title="Fit every visible node and link in the editor"
            >
              Fit
            </button>
            <button
              type="button"
              onClick={() => store.requestZoom(1 / 1.25)}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[10px] text-muted hover:border-line-strong hover:text-text"
              title="Zoom out"
              aria-label="Zoom out"
            >
              −
            </button>
            <button
              type="button"
              onClick={() => store.requestZoom(1.25)}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[10px] text-muted hover:border-line-strong hover:text-text"
              title="Zoom in"
              aria-label="Zoom in"
            >
              +
            </button>
            <button
              type="button"
              aria-pressed={ui.pinned}
              onClick={() => store.setPinned(!ui.pinned)}
              className={cx(
                "inline-flex min-h-6 items-center border px-2 font-mono text-[10px]",
                ui.pinned
                  ? "border-selection/70 bg-selection/10 text-selection-strong"
                  : "border-line-soft bg-panel-soft/40 text-muted hover:border-line-strong hover:text-text",
              )}
              title="Keep dragged node positions across reloads for this snapshot"
            >
              {ui.pinned ? "Pinned" : "Pin positions"}
            </button>
            <button
              type="button"
              onClick={() => store.requestReset()}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[10px] text-muted hover:border-line-strong hover:text-text"
              title="Clear filters and pinned positions, then fit the graph"
            >
              Reset
            </button>
          </div>
          <p className="text-[9px] leading-relaxed text-faint">
            Drag a node to move it; drag empty space to pan; wheel to zoom;
            double-click a node to focus.
          </p>
        </section>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor: D3 force-directed canvas
// ---------------------------------------------------------------------------

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  model: TopologyNodeModel;
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  id: string;
  model: TopologyLinkModel;
  sourceId: string;
  targetId: string;
}

interface HoverState {
  kind: "node" | "edge";
  id: string;
  x: number;
  y: number;
}

function categoryAnchors(nodes: SimNode[]): Map<string, { x: number; y: number }> {
  const categories = [...new Set(nodes.map((node) => node.model.category))].sort();
  const radius = 130 + Math.min(220, nodes.length * 2);
  return new Map(
    categories.map((category, index) => {
      const angle = (index / Math.max(1, categories.length)) * Math.PI * 2 - Math.PI / 2;
      return [
        category,
        { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius },
      ] as const;
    }),
  );
}

function linkPath(
  source: SimNode,
  target: SimNode,
  offset: number,
): { path: string; x: number; y: number } {
  const sourceRadius = nodeRadius(source.model) + 2;
  const targetRadius = nodeRadius(target.model) + 4;
  const sourceX = source.x ?? 0;
  const sourceY = source.y ?? 0;
  const targetX = target.x ?? 0;
  const targetY = target.y ?? 0;
  if (source.id === target.id) {
    const radius = sourceRadius + 9;
    return {
      path: `M ${sourceX} ${sourceY - radius} C ${sourceX + radius * 1.9} ${
        sourceY - radius * 2.2
      }, ${sourceX + radius * 1.9} ${sourceY + radius * 2.2}, ${sourceX} ${
        sourceY + radius
      }`,
      x: sourceX,
      y: sourceY + radius,
    };
  }

  const dx = targetX - sourceX;
  const dy = targetY - sourceY;
  const distance = Math.max(0.001, Math.hypot(dx, dy));
  const ux = dx / distance;
  const uy = dy / distance;
  const startX = sourceX + ux * sourceRadius;
  const startY = sourceY + uy * sourceRadius;
  const endX = targetX - ux * targetRadius;
  const endY = targetY - uy * targetRadius;

  if (Math.abs(offset) < 0.01) {
    return {
      path: `M ${startX} ${startY} L ${endX} ${endY}`,
      x: endX,
      y: endY,
    };
  }

  const normalX = -uy;
  const normalY = ux;
  const controlX = (startX + endX) / 2 + normalX * offset * 2;
  const controlY = (startY + endY) / 2 + normalY * offset * 2;
  return {
    path: `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`,
    x: endX,
    y: endY,
  };
}

export function TopologyEditor(props: FeatureProps): JSX.Element {
  const model = useTopologyModel(props);
  const [ui, store] = useTopologyUi(props.state.snapshot.name);
  const selection = topologySelection(props);
  const visible = useMemo(
    () => applyTopologyFilters(model, ui.filters),
    [model, ui.filters],
  ) as TopologyVisibleGraph;

  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const sceneRef = useRef<SVGGElement | null>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | undefined>(
    undefined,
  );
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | undefined>(
    undefined,
  );
  const simNodesRef = useRef<SimNode[]>([]);
  const uiRef = useRef(ui);
  const suppressClickRef = useRef(false);
  const dragMovedRef = useRef(false);
  const dragResetTimerRef = useRef<number | undefined>(undefined);
  const lastFitRef = useRef("");
  const fitTokenRef = useRef(ui.fitToken);
  const zoomTokenRef = useRef(ui.zoomToken);

  const [size, setSize] = useState({ width: 0, height: 0 });
  const [tick, setTick] = useState(0);
  const [zoomK, setZoomK] = useState(1);
  const [hover, setHover] = useState<HoverState | undefined>(undefined);
  const [focusedNodeId, setFocusedNodeId] = useState<string | undefined>(
    undefined,
  );
  const [hoveredNodeId, setHoveredNodeId] = useState<string | undefined>(
    undefined,
  );
  const [hoveredLinkId, setHoveredLinkId] = useState<string | undefined>(
    undefined,
  );

  useEffect(() => {
    uiRef.current = ui;
  }, [ui]);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (!rect) return;
      setSize({
        width: Math.max(1, Math.round(rect.width)),
        height: Math.max(1, Math.round(rect.height)),
      });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Create and warm the force simulation. Coordinates are view state; the
  // builder never sees them.
  useEffect(() => {
    const positions = uiRef.current.positions;
    const pinned = uiRef.current.pinned;
    const nodes: SimNode[] = model.nodes.map((node, index) => {
      const saved = positions[node.id];
      const angle = index * 2.399963229728653;
      const distance = 24 * Math.sqrt(index + 1);
      const x = saved?.x ?? Math.cos(angle) * distance;
      const y = saved?.y ?? Math.sin(angle) * distance;
      return {
        id: node.id,
        model: node,
        x,
        y,
        fx: pinned && saved ? saved.x : null,
        fy: pinned && saved ? saved.y : null,
      };
    });
    const links: SimLink[] = model.links.map((link) => ({
      id: link.id,
      model: link,
      source: link.source,
      target: link.target,
      sourceId: link.source,
      targetId: link.target,
    }));

    const anchors = categoryAnchors(nodes);
    const simulation = d3
      .forceSimulation<SimNode>(nodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimLink>(links)
          .id((node) => node.id)
          .distance((link) => (link.model.kind === "containment" ? 92 : 118))
          .strength((link) => (link.model.kind === "containment" ? 0.45 : 0.2)),
      )
      .force("charge", d3.forceManyBody<SimNode>().strength(-260))
      .force("center", d3.forceCenter<SimNode>(0, 0))
      .force(
        "collide",
        d3.forceCollide<SimNode>().radius((node) => nodeRadius(node.model) + 7),
      )
      .force(
        "x",
        d3
          .forceX<SimNode>((node) => anchors.get(node.model.category)?.x ?? 0)
          .strength(0.045),
      )
      .force(
        "y",
        d3
          .forceY<SimNode>((node) => anchors.get(node.model.category)?.y ?? 0)
          .strength(0.045),
      )
      .alphaDecay(0.05)
      .velocityDecay(0.36);

    simulation.stop();
    for (let step = 0; step < 220; step += 1) simulation.tick();
    simulation.alpha(0.14).restart();

    simulationRef.current = simulation;
    simNodesRef.current = nodes;

    let frame = 0;
    const renderTick = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        frame = 0;
        setTick((value) => value + 1);
      });
    };
    simulation.on("tick", renderTick);
    setTick((value) => value + 1);

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      simulation.on("tick", null);
      simulation.stop();
      simulationRef.current = undefined;
    };
  }, [model]);

  // Zoom/pan. The scene transform is written imperatively so a simulation tick
  // does not reconcile the viewport.
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const behavior = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.15, 4])
      .on("zoom", (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
        if (sceneRef.current) {
          sceneRef.current.setAttribute("transform", event.transform.toString());
        }
        setZoomK(event.transform.k);
      });
    zoomRef.current = behavior;
    const root = d3.select(svg);
    root.call(behavior);
    root.on("dblclick.zoom", null);
    return () => {
      root.on(".zoom", null);
      zoomRef.current = undefined;
    };
  }, []);

  // Apply pin state without restarting the simulation on every saved position.
  useEffect(() => {
    const simulation = simulationRef.current;
    const nodes = simNodesRef.current;
    if (!simulation || !nodes.length) return;
    if (ui.pinned) {
      const next: Record<string, { x: number; y: number }> = {};
      for (const node of nodes) {
        const saved = ui.positions[node.id];
        const x = saved?.x ?? node.x ?? 0;
        const y = saved?.y ?? node.y ?? 0;
        node.x = x;
        node.y = y;
        node.fx = x;
        node.fy = y;
        next[node.id] = { x, y };
      }
      const hasMissing = nodes.some((node) => !ui.positions[node.id]);
      if (hasMissing) store.setPositions(next);
      setTick((value) => value + 1);
    } else {
      for (const node of nodes) {
        node.fx = null;
        node.fy = null;
      }
      simulation.alpha(0.18).restart();
    }
  }, [ui.pinned, ui.hydrated, store]);

  const fitGraph = useCallback(() => {
    const svg = svgRef.current;
    const behavior = zoomRef.current;
    if (!svg || !behavior) return;
    const nodes = (visible.nodes.length ? visible.nodes : model.nodes)
      .map((node) => simNodesRef.current.find((sim) => sim.id === node.id))
      .filter((node): node is SimNode => Boolean(node));
    if (!nodes.length) return;

    let minX = Number.POSITIVE_INFINITY;
    let minY = Number.POSITIVE_INFINITY;
    let maxX = Number.NEGATIVE_INFINITY;
    let maxY = Number.NEGATIVE_INFINITY;
    for (const node of nodes) {
      const radius = nodeRadius(node.model);
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      minX = Math.min(minX, x - radius);
      minY = Math.min(minY, y - radius);
      maxX = Math.max(maxX, x + radius);
      maxY = Math.max(maxY, y + radius);
    }
    const width = svg.clientWidth || size.width || 800;
    const height = svg.clientHeight || size.height || 600;
    const padding = 64;
    const boundsWidth = Math.max(1, maxX - minX + padding * 2);
    const boundsHeight = Math.max(1, maxY - minY + padding * 2);
    const k = Math.max(
      0.15,
      Math.min(2.4, Math.min(width / boundsWidth, height / boundsHeight)),
    );
    const tx = width / 2 - ((minX + maxX) / 2) * k;
    const ty = height / 2 - ((minY + maxY) / 2) * k;
    d3.select(svg).call(
      behavior.transform,
      d3.zoomIdentity.translate(tx, ty).scale(k),
    );
  }, [model.nodes, size.height, size.width, visible.nodes]);

  const fitRef = useRef(fitGraph);
  useEffect(() => {
    fitRef.current = fitGraph;
  }, [fitGraph]);

  // Initial fit once the simulation has positions and the editor has a size.
  useEffect(() => {
    if (!size.width || !size.height) return;
    if (lastFitRef.current === model.graphKey) return;
    lastFitRef.current = model.graphKey;
    const frame = window.requestAnimationFrame(() => fitRef.current());
    return () => window.cancelAnimationFrame(frame);
  }, [model.graphKey, size.height, size.width]);

  useEffect(() => {
    if (ui.fitToken === 0 || ui.fitToken === fitTokenRef.current) return;
    fitTokenRef.current = ui.fitToken;
    const frame = window.requestAnimationFrame(() => fitRef.current());
    return () => window.cancelAnimationFrame(frame);
  }, [ui.fitToken]);

  const zoomBy = useCallback((factor: number) => {
    const svg = svgRef.current;
    const behavior = zoomRef.current;
    if (!svg || !behavior) return;
    d3.select(svg).call(behavior.scaleBy, factor);
  }, []);

  useEffect(() => {
    if (ui.zoomToken === zoomTokenRef.current) return;
    zoomTokenRef.current = ui.zoomToken;
    zoomBy(ui.zoomFactor);
  }, [ui.zoomFactor, ui.zoomToken, zoomBy]);

  const focusNode = useCallback((node: SimNode) => {
    const svg = svgRef.current;
    const behavior = zoomRef.current;
    if (!svg || !behavior) return;
    const width = svg.clientWidth || 800;
    const height = svg.clientHeight || 600;
    const k = 1.7;
    const tx = width / 2 - (node.x ?? 0) * k;
    const ty = height / 2 - (node.y ?? 0) * k;
    d3.select(svg).call(
      behavior.transform,
      d3.zoomIdentity.translate(tx, ty).scale(k),
    );
  }, []);

  // Node dragging is attached with d3-drag to the rendered node groups.
  useEffect(() => {
    const simulation = simulationRef.current;
    if (!simulation) return;
    const nodesById = new Map(simNodesRef.current.map((node) => [node.id, node]));
    const drag = d3
      .drag<SVGGElement, SimNode>()
      .clickDistance(4)
      .on("start", (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>) => {
        const node = event.subject;
        if (!node) return;
        dragMovedRef.current = false;
        suppressClickRef.current = false;
        if (!event.active) simulation.alphaTarget(0.22).restart();
        node.fx = node.x;
        node.fy = node.y;
      })
      .on("drag", (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>) => {
        const node = event.subject;
        if (!node) return;
        if (
          Math.abs(event.x - (node.x ?? 0)) > 0.5 ||
          Math.abs(event.y - (node.y ?? 0)) > 0.5
        ) {
          dragMovedRef.current = true;
        }
        node.fx = event.x;
        node.fy = event.y;
        node.x = event.x;
        node.y = event.y;
        setTick((value) => value + 1);
      })
      .on("end", (event: d3.D3DragEvent<SVGGElement, SimNode, SimNode>) => {
        const node = event.subject;
        if (!node) return;
        if (!event.active) simulation.alphaTarget(0);
        if (uiRef.current.pinned) {
          node.fx = node.x;
          node.fy = node.y;
          store.setPosition(node.id, { x: node.x ?? 0, y: node.y ?? 0 });
        } else {
          node.fx = null;
          node.fy = null;
          simulation.alpha(0.12).restart();
        }
        if (dragMovedRef.current) {
          suppressClickRef.current = true;
          if (dragResetTimerRef.current) {
            window.clearTimeout(dragResetTimerRef.current);
          }
          dragResetTimerRef.current = window.setTimeout(() => {
            suppressClickRef.current = false;
          }, 80);
        }
      });
    d3.select(svgRef.current)
      .selectAll<SVGGElement, unknown>("g[data-topology-node-id]")
      .each(function attachDrag() {
        const id = this.getAttribute("data-topology-node-id");
        const node = id ? nodesById.get(id) : undefined;
        if (node) {
          d3.select<SVGGElement, SimNode>(this).datum(node).call(drag);
        }
      });
    return () => {
      if (dragResetTimerRef.current) {
        window.clearTimeout(dragResetTimerRef.current);
      }
    };
  }, [store, visible.nodes, ui.pinned]);

  const simById = new Map(
    simNodesRef.current.map((node) => [node.id, node] as const),
  );
  const selectedNodeName =
    selection?.kind === "node" ? selection.name : undefined;
  const selectedEdgeName =
    selection?.kind === "edge" ? selection.name : undefined;

  const adjacentNames = useMemo(() => {
    const names = new Set<string>();
    if (selectedNodeName) {
      for (const link of visible.links) {
        if (link.sourceName === selectedNodeName) names.add(link.targetName);
        if (link.targetName === selectedNodeName) names.add(link.sourceName);
      }
    }
    if (selectedEdgeName) {
      for (const link of visible.links) {
        if (link.kind === "edge" && link.edgeName === selectedEdgeName) {
          names.add(link.sourceName);
          names.add(link.targetName);
        }
      }
    }
    return names;
  }, [selectedEdgeName, selectedNodeName, visible.links]);

  const ambientLabels = useMemo(() => {
    const labels = new Set<string>();
    const ranked = [...visible.nodes].sort(
      (left, right) =>
        right.degree - left.degree || left.name.localeCompare(right.name),
    );
    for (const node of ranked.slice(0, 18)) labels.add(node.id);
    for (const node of visible.nodes) {
      if (node.abstract) labels.add(node.id);
    }
    return labels;
  }, [visible.nodes]);

  // Label placement is a screen-space collision check. Selected, hovered and
  // focused labels are always kept; ambient labels yield when they would
  // overlap a more important one.
  const labelIds = (() => {
    const forced = new Set<string>();
    if (selectedNodeName) forced.add(`topology:node:${selectedNodeName}`);
    if (hoveredNodeId) forced.add(hoveredNodeId);
    if (focusedNodeId && model.nodeById.has(focusedNodeId)) {
      forced.add(focusedNodeId);
    }
    if (selectedEdgeName) {
      for (const link of visible.links) {
        if (link.kind === "edge" && link.edgeName === selectedEdgeName) {
          forced.add(link.source);
          forced.add(link.target);
        }
      }
    }

    const candidates = visible.nodes
      .filter((node) => ambientLabels.has(node.id) || forced.has(node.id))
      .sort((left, right) => {
        const forcedDelta =
          Number(forced.has(right.id)) - Number(forced.has(left.id));
        return (
          forcedDelta ||
          right.degree - left.degree ||
          left.name.localeCompare(right.name)
        );
      });

    const boxes: Array<{ left: number; right: number; top: number; bottom: number }> =
      [];
    const visibleLabels = new Set<string>();
    for (const node of candidates) {
      const sim = simById.get(node.id);
      if (!sim) continue;
      const radius = nodeRadius(node);
      const width = Math.max(16, node.label.length * 5.6 + 8);
      const x = sim.x ?? 0;
      const y = sim.y ?? 0;
      const box = {
        left: x - width / 2,
        right: x + width / 2,
        top: y + radius + 2,
        bottom: y + radius + 15,
      };
      const overlaps = boxes.some(
        (other) =>
          !(
            box.right < other.left ||
            box.left > other.right ||
            box.bottom < other.top ||
            box.top > other.bottom
          ),
      );
      if (overlaps && !forced.has(node.id)) continue;
      boxes.push(box);
      visibleLabels.add(node.id);
    }
    return visibleLabels;
  })();

  const linkOffsets = useMemo(() => {
    const offsets = new Map<string, number>();
    const groups = new Map<string, TopologyLinkModel[]>();
    for (const link of visible.links) {
      if (link.source === link.target) continue;
      const key =
        link.source < link.target
          ? `${link.source}\u0000${link.target}`
          : `${link.target}\u0000${link.source}`;
      const group = groups.get(key) ?? [];
      group.push(link);
      groups.set(key, group);
    }
    for (const group of groups.values()) {
      if (group.length < 2) continue;
      group.sort((left, right) => left.id.localeCompare(right.id));
      group.forEach((link, index) => {
        offsets.set(link.id, (index - (group.length - 1) / 2) * 18);
      });
    }
    return offsets;
  }, [visible.links]);

  const hasSelection = Boolean(selection);
  const hoverEntity: TopologyEntity | undefined = hover
    ? hover.kind === "node"
      ? model.nodeById.get(hover.id)
      : model.linkById.get(hover.id)
    : undefined;

  const updateHover = (kind: HoverState["kind"], id: string, event: ReactMouseEvent) => {
    const point = pointerPosition(containerRef.current, event);
    if (point) setHover({ kind, id, ...point });
  };

  const selectNode = (node: TopologyNodeModel) => {
    if (suppressClickRef.current) return;
    writeSelection(props, "node", node.name);
  };

  const selectLink = (link: TopologyLinkModel) => {
    if (suppressClickRef.current) return;
    if (link.kind === "containment") {
      writeSelection(props, "node", link.targetName);
      return;
    }
    writeSelection(props, "edge", link.edgeName ?? link.name);
  };

  const showNodeMarkers = ui.filters.kinds.node;
  const visibleCount = visible.nodes.length + visible.links.length;

  return (
    <div
      ref={containerRef}
      data-testid="topology-editor"
      data-level="panel"
      className="relative h-full min-h-0 w-full select-none overflow-hidden bg-abyss"
      aria-label="Topology force graph"
    >
      <svg
        ref={svgRef}
        data-testid="topology-canvas"
        className="block h-full w-full touch-none cursor-grab select-none"
        role="img"
        aria-label={`Topology force graph with ${visible.nodes.length} nodes and ${visible.links.length} links`}
      >
        <defs>
          <pattern id="topology-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.7" fill={theme.lineSoft} opacity="0.75" />
          </pattern>
          <marker
            id="topology-arrow"
            viewBox="0 -4 8 8"
            refX="7"
            refY="0"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0,-4 L8,0 L0,4" fill={theme.edge} />
          </marker>
          <marker
            id="topology-arrow-accent"
            viewBox="0 -4 8 8"
            refX="7"
            refY="0"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0,-4 L8,0 L0,4" fill={theme.accentStrong} />
          </marker>
          <marker
            id="topology-arrow-selection"
            viewBox="0 -4 8 8"
            refX="7"
            refY="0"
            markerWidth="5"
            markerHeight="5"
            orient="auto"
          >
            <path d="M0,-4 L8,0 L0,4" fill={theme.selection} />
          </marker>
          <marker
            id="topology-arrow-soft"
            viewBox="0 -4 8 8"
            refX="7"
            refY="0"
            markerWidth="4"
            markerHeight="4"
            orient="auto"
          >
            <path d="M0,-4 L8,0 L0,4" fill={theme.lineStrong} />
          </marker>
        </defs>

        <rect width="100%" height="100%" fill="url(#topology-grid)" pointerEvents="none" />

        <g ref={sceneRef}>
          <g data-topology-links>
            {visible.links.map((link) => {
              const source = simById.get(link.source);
              const target = simById.get(link.target);
              if (!source || !target) return null;
              const geometry = linkPath(
                source,
                target,
                linkOffsets.get(link.id) ?? 0,
              );
              const selected =
                link.kind === "edge" && link.edgeName === selectedEdgeName;
              const hovered = hoveredLinkId === link.id || focusedNodeId === link.id;
              const incident =
                Boolean(selectedNodeName) &&
                (link.sourceName === selectedNodeName ||
                  link.targetName === selectedNodeName);
              const dim = hasSelection && !selected && !incident;
              const tone = selected
                ? theme.selection
                : hovered
                  ? theme.accentStrong
                  : incident
                    ? theme.accent
                    : link.kind === "containment"
                      ? theme.lineStrong
                      : link.decisionStatus === "rejected"
                        ? theme.critical
                        : link.decisionStatus === "open"
                          ? theme.medium
                          : theme.edge;
              const marker = selected
                ? "url(#topology-arrow-selection)"
                : hovered
                  ? "url(#topology-arrow-accent)"
                  : link.kind === "containment"
                    ? "url(#topology-arrow-soft)"
                    : "url(#topology-arrow)";
              const opacity = dim
                ? 0.08
                : link.kind === "containment"
                  ? 0.34
                  : selected || hovered
                    ? 0.95
                    : incident
                      ? 0.8
                      : 0.55;
              return (
                <g key={link.id}>
                  <path
                    d={geometry.path}
                    fill="none"
                    stroke={tone}
                    strokeWidth={selected ? 2.6 : hovered || incident ? 1.8 : 1}
                    strokeOpacity={opacity}
                    strokeDasharray={link.kind === "containment" ? "4 3" : undefined}
                    markerEnd={marker}
                    vectorEffect="non-scaling-stroke"
                    pointerEvents="none"
                  />
                  <path
                    data-topology-link={link.kind === "edge" ? link.edgeName : link.name}
                    d={geometry.path}
                    fill="none"
                    stroke="transparent"
                    strokeWidth={12}
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                    pointerEvents="stroke"
                    tabIndex={0}
                    role="button"
                    aria-label={`${
                      link.kind === "containment" ? "Containment" : "Relationship"
                    } ${link.edgeName ?? link.name}, ${link.sourceName} to ${link.targetName}`}
                    onFocus={() => setFocusedNodeId(link.id)}
                    onBlur={() => setFocusedNodeId(undefined)}
                    onClick={(event) => {
                      event.stopPropagation();
                      selectLink(link);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        selectLink(link);
                      }
                    }}
                    onMouseEnter={(event) => {
                      setHoveredLinkId(link.id);
                      updateHover("edge", link.id, event);
                    }}
                    onMouseMove={(event) => updateHover("edge", link.id, event)}
                    onMouseLeave={() => {
                      setHoveredLinkId(undefined);
                      setHover(undefined);
                    }}
                  >
                    <title>
                      {`${link.label} · ${link.sourceName} → ${link.targetName}${
                        link.findings.total
                          ? ` · ${link.findings.total} finding${
                              link.findings.total === 1 ? "" : "s"
                            }`
                          : ""
                      }${link.decisionStatus ? ` · decision ${link.decisionStatus}` : ""}`}
                    </title>
                  </path>
                </g>
              );
            })}
          </g>

          <g data-topology-nodes>
            {showNodeMarkers
              ? visible.nodes.map((node) => {
                  const sim = simById.get(node.id);
                  if (!sim) return null;
                  const radius = nodeRadius(node);
                  const selected = selectedNodeName === node.name;
                  const adjacent = adjacentNames.has(node.name);
                  const hovered = hoveredNodeId === node.id;
                  const focused = focusedNodeId === node.id;
                  const dim = hasSelection && !selected && !adjacent;
                  const base = nodeFill(node);
                  const ring = selected
                    ? theme.selection
                    : hovered || focused
                      ? theme.accentStrong
                      : statusColor(node) ?? base;
                  const showLabel = labelIds.has(node.id);
                  return (
                    <g
                      key={node.id}
                      data-topology-node-id={node.id}
                      data-topology-node={node.name}
                      transform={`translate(${sim.x ?? 0} ${sim.y ?? 0})`}
                      opacity={dim ? 0.2 : 1}
                      tabIndex={0}
                      role="button"
                      aria-pressed={selected}
                      aria-label={`${node.label}, ${node.abstract ? "abstract category" : "node"}, ${node.category}, ${node.degree} links, ${formatStatus(node)}`}
                      onClick={(event) => {
                        event.stopPropagation();
                        selectNode(node);
                      }}
                      onDoubleClick={(event) => {
                        event.stopPropagation();
                        selectNode(node);
                        focusNode(sim);
                      }}
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          selectNode(node);
                        }
                      }}
                      onFocus={() => setFocusedNodeId(node.id)}
                      onBlur={() => setFocusedNodeId(undefined)}
                      onMouseEnter={(event) => {
                        setHoveredNodeId(node.id);
                        updateHover("node", node.id, event);
                      }}
                      onMouseMove={(event) => updateHover("node", node.id, event)}
                      onMouseLeave={() => {
                        setHoveredNodeId(undefined);
                        setHover(undefined);
                      }}
                    >
                      <title>
                        {`${node.label} (${node.name}) · ${
                          node.abstract ? "abstract category" : "node"
                        } · ${node.category} · ${node.degree} links · ${
                          node.properties
                        } properties · ${formatStatus(node)}`}
                      </title>
                      {selected || hovered || focused ? (
                        <circle
                          r={radius + 3.5}
                          fill="none"
                          stroke={selected ? theme.selection : theme.accentStrong}
                          strokeWidth={selected ? 1.6 : 1.2}
                          vectorEffect="non-scaling-stroke"
                          pointerEvents="none"
                        />
                      ) : null}
                      <circle
                        r={radius}
                        fill={base}
                        fillOpacity={node.abstract ? 0.08 : 0.22}
                        stroke={ring}
                        strokeWidth={node.abstract ? 1.4 : 1}
                        strokeDasharray={node.abstract ? "3 2" : undefined}
                        vectorEffect="non-scaling-stroke"
                      />
                      {node.findings.total ? (
                        <g
                          transform={`translate(${radius * 0.72} ${-radius * 0.72})`}
                          pointerEvents="none"
                        >
                          <circle
                            r={Math.min(6.5, 2.5 + Math.log2(node.findings.total + 1))}
                            fill={severityColor[node.findings.worst ?? "info"]}
                            stroke={theme.page}
                            strokeWidth={1}
                          />
                          <text
                            textAnchor="middle"
                            dominantBaseline="central"
                            fill={theme.page}
                            fontSize={Math.min(7, 4 + Math.log2(node.findings.total + 1))}
                            fontFamily="var(--font-mono)"
                          >
                            {node.findings.total > 9 ? "9+" : node.findings.total}
                          </text>
                        </g>
                      ) : node.decisionStatus ? (
                        <circle
                          cx={radius * 0.72}
                          cy={radius * 0.72}
                          r={2.5}
                          fill={DECISION_COLOR[node.decisionStatus]}
                          stroke={theme.page}
                          strokeWidth={0.8}
                          pointerEvents="none"
                        />
                      ) : null}
                      {showLabel ? (
                        <text
                          y={radius + 12}
                          textAnchor="middle"
                          fill={
                            selected
                              ? theme.selection
                              : hovered || focused
                                ? theme.text
                                : theme.muted
                          }
                          fontSize={10.5}
                          fontFamily="var(--font-sans)"
                          stroke={theme.page}
                          strokeWidth={3}
                          strokeLinejoin="round"
                          paintOrder="stroke"
                          className="pointer-events-none select-none"
                        >
                          {node.label}
                        </text>
                      ) : null}
                    </g>
                  );
                })
              : null}
          </g>
        </g>
      </svg>

      <div className="pointer-events-none absolute top-2 left-2 z-10 flex flex-wrap items-center gap-1">
        {hasSelection ? (
          <span className="pointer-events-auto inline-flex items-center gap-1 border border-line-soft bg-panel/95 px-1.5 py-0.5 font-mono text-[9px] text-selection-strong">
            selected · {selection?.name}
          </span>
        ) : null}
        {ui.pinned ? (
          <span className="pointer-events-auto inline-flex items-center border border-selection/60 bg-selection/10 px-1.5 py-0.5 font-mono text-[9px] text-selection-strong">
            positions pinned
          </span>
        ) : null}
      </div>

      <div className="absolute bottom-2 left-2 z-20 flex items-stretch border border-line-soft bg-panel/95">
        <button
          type="button"
          onClick={() => zoomBy(1 / 1.25)}
          className="flex size-6 items-center justify-center border-r border-line text-muted hover:bg-panel-soft hover:text-text"
          aria-label="Zoom out"
          title="Zoom out"
        >
          −
        </button>
        <span className="flex w-12 items-center justify-center border-r border-line font-mono text-[10px] text-muted tabular-nums">
          {Math.round(zoomK * 100)}%
        </span>
        <button
          type="button"
          onClick={() => zoomBy(1.25)}
          className="flex size-6 items-center justify-center border-r border-line text-muted hover:bg-panel-soft hover:text-text"
          aria-label="Zoom in"
          title="Zoom in"
        >
          +
        </button>
        <button
          type="button"
          onClick={() => fitRef.current()}
          className="flex size-6 items-center justify-center text-muted hover:bg-panel-soft hover:text-text"
          aria-label="Fit graph"
          title="Fit graph"
        >
          ⛶
        </button>
      </div>

      {visibleCount === 0 ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="border border-line-soft bg-panel/95 px-3 py-2 font-mono text-[11px] text-muted">
            No topology entities match these filters.
          </p>
        </div>
      ) : null}

      {hover && hoverEntity ? (
        <div
          className="pointer-events-none absolute z-30 w-[270px] overflow-hidden border border-line-soft bg-panel/98 shadow-lg"
          style={{ left: hover.x + 14, top: hover.y + 14 }}
        >
          <p className="border-b border-line-soft px-2 py-1 font-mono text-[10px] break-words text-accent-strong">
            {hoverEntity.label}
            {hoverEntity.label !== hoverEntity.name ? (
              <span className="text-faint"> · {hoverEntity.name}</span>
            ) : null}
          </p>
          <div className="space-y-0.5 px-2 py-1 font-mono text-[9px] text-muted">
            {hoverEntity.kind === "node" ? (
              <>
                <p>
                  node · {hoverEntity.abstract ? "abstract" : "concrete"} ·{" "}
                  {hoverEntity.category}
                </p>
                <p>
                  {hoverEntity.degree} links · {hoverEntity.properties} properties
                </p>
              </>
            ) : (
              <>
                <p>
                  {hoverEntity.kind === "containment" ? "containment" : "edge"} ·{" "}
                  {hoverEntity.sourceName} → {hoverEntity.targetName}
                </p>
                {hoverEntity.edgeName ? <p>{hoverEntity.edgeName}</p> : null}
              </>
            )}
            <p>
              semantics {hoverEntity.hasSemantics ? "present" : "missing"} ·{" "}
              {hoverEntity.findings.total} finding
              {hoverEntity.findings.total === 1 ? "" : "s"}
            </p>
            {hoverEntity.decisionStatus ? (
              <p>decision {hoverEntity.decisionStatus}</p>
            ) : null}
            {hoverEntity.findings.worst ? (
              <p className="text-[8px]">
                strongest finding {SEVERITY_LABEL[hoverEntity.findings.worst]}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bottom panel
// ---------------------------------------------------------------------------

function SummaryField({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="w-20 shrink-0 text-[9px] tracking-[0.06em] text-faint uppercase">
        {label}
      </span>
      <span className="min-w-0 flex-1 truncate font-mono text-[10px] text-text">
        {value}
      </span>
    </div>
  );
}

function SemanticsBlock({ entity }: { entity: TopologyEntity }) {
  const { semantics } = entity;
  if (!semantics.present) {
    return (
      <p className="text-[10px] text-faint">
        No semantics attached to this {entity.kind}.
      </p>
    );
  }
  return (
    <div className="space-y-1 text-[10px] leading-relaxed text-muted">
      {semantics.claims.length ? (
        <div>
          <p className="text-[9px] tracking-[0.06em] text-faint uppercase">
            Claims · {semantics.claimCount}
          </p>
          {semantics.claims.slice(0, 3).map((claim) => (
            <p key={claim} className="line-clamp-2">
              {claim}
            </p>
          ))}
        </div>
      ) : null}
      {semantics.frames.length ? (
        <div>
          <p className="text-[9px] tracking-[0.06em] text-faint uppercase">
            Frames · {semantics.frameCount}
          </p>
          {semantics.frames.slice(0, 2).map((frame) => (
            <p key={frame} className="line-clamp-2">
              {frame}
            </p>
          ))}
        </div>
      ) : null}
      {semantics.limitations.length ? (
        <div>
          <p className="text-[9px] tracking-[0.06em] text-faint uppercase">
            Limitations · {semantics.limitationCount}
          </p>
          {semantics.limitations.slice(0, 2).map((limitation) => (
            <p key={limitation} className="line-clamp-2">
              {limitation}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function TopologyBottom(props: FeatureProps): JSX.Element {
  const model = useTopologyModel(props);
  const selection = topologySelection(props);
  const entity = findTopologyEntity(model, selection);
  const raw =
    entity && isTopologyNode(entity)
      ? props.state.index.topologyNodesByName.get(entity.name)
      : entity
        ? props.state.index.topologyEdgesByName.get(entity.edgeName ?? entity.name)
        : undefined;

  if (!entity) {
    return (
      <div className="flex h-full min-h-0 flex-col bg-panel">
        <header className="flex items-baseline justify-between border-b border-line-soft px-3 py-1.5">
          <h2 className="text-[11px] font-semibold tracking-[0.08em] text-text uppercase">
            Selection
          </h2>
          <span className="font-mono text-[9px] text-faint">
            {model.stats.nodes} nodes · {model.stats.edgeLinks} relations ·{" "}
            {model.stats.semantics} with semantics
          </span>
        </header>
        <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto px-3 py-2">
          <p className="text-[10px] text-muted">
            Select a node or relation in the force graph to inspect its labels,
            semantics, findings and decision state. Clicking a node or edge also
            sets the workbench selection for the other activities.
          </p>
          <div className="mt-2 grid gap-1">
            <SummaryField label="Nodes" value={model.stats.nodes} />
            <SummaryField label="Abstract" value={model.stats.abstractNodes} />
            <SummaryField label="Relations" value={model.stats.edgeLinks} />
            <SummaryField label="Containment" value={model.stats.containmentLinks} />
            <SummaryField label="Findings" value={model.stats.findings} />
            <SummaryField label="Decisions" value={model.stats.decisions} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col bg-panel">
      <header className="flex items-baseline justify-between gap-2 border-b border-line-soft px-3 py-1.5">
        <div className="flex min-w-0 items-baseline gap-2">
          <h2 className="text-[11px] font-semibold tracking-[0.08em] text-text uppercase">
            {entity.kind === "node" ? "Node" : "Relation"}
          </h2>
          <span className="truncate font-mono text-[11px] text-accent-strong">
            {entity.label}
          </span>
          <span className="truncate font-mono text-[9px] text-faint">
            {entity.name}
          </span>
        </div>
        <button
          type="button"
          onClick={() => clearSelection(props)}
          className="shrink-0 border border-line-soft px-1.5 py-0.5 font-mono text-[9px] text-muted hover:border-line-strong hover:text-text"
        >
          Clear
        </button>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(220px,0.9fr)_minmax(260px,1.1fr)] gap-[2px] overflow-hidden bg-gutter">
        <div className="thin-scrollbar min-h-0 overflow-y-auto bg-panel px-3 py-2">
          <div className="grid gap-1">
            <SummaryField
              label="Kind"
              value={
                entity.kind === "node"
                  ? entity.abstract
                    ? "abstract node"
                    : "node"
                  : entity.kind === "containment"
                    ? "containment"
                    : "edge"
              }
            />
            <SummaryField label="Category" value={entity.category} />
            {entity.kind === "node" ? (
              <>
                <SummaryField label="Degree" value={entity.degree} />
                <SummaryField label="Properties" value={entity.properties} />
                <SummaryField label="Children" value={entity.children} />
              </>
            ) : (
              <>
                <SummaryField label="Source" value={entity.sourceName} />
                <SummaryField label="Target" value={entity.targetName} />
              </>
            )}
            <SummaryField
              label="Labels"
              value={entity.labels.length ? entity.labels.join(", ") : "—"}
            />
            <SummaryField
              label="Semantics"
              value={
                entity.hasSemantics
                  ? `${entity.semantics.claimCount} claims · ${entity.semantics.frameCount} frames · ${entity.semantics.limitationCount} limitations`
                  : "missing"
              }
            />
            <SummaryField
              label="Findings"
              value={
                entity.findings.total
                  ? `${entity.findings.total} (${entity.findings.rules.join(", ")})`
                  : "none"
              }
            />
            <SummaryField
              label="Decision"
              value={
                entity.decisionStatus
                  ? `${entity.decisionStatus}${entity.decisionIds.length > 1 ? ` (+${entity.decisionIds.length - 1})` : ""}`
                  : "none"
              }
            />
          </div>
          <div className="mt-2 border-t border-line-soft pt-2">
            <SemanticsBlock entity={entity} />
          </div>
        </div>
        <div className="flex min-h-0 flex-col bg-inset">
          <div className="flex items-center justify-between border-b border-line-soft px-2 py-1">
            <span className="text-[9px] tracking-[0.08em] text-faint uppercase">
              JSON
            </span>
            <span className="font-mono text-[9px] text-faint">
              blueprint.graph.{entity.kind === "node" ? "nodes" : "edges"} ·{" "}
              {entity.name}
            </span>
          </div>
          <pre className="thin-scrollbar min-h-0 flex-1 overflow-auto px-2 py-1 font-mono text-[9px] leading-relaxed text-muted">
            {JSON.stringify(raw ?? entity, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}
