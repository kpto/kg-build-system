"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
} from "react";
import type { JSX, MouseEvent as ReactMouseEvent, ReactNode } from "react";
import * as d3 from "d3";

import type { WorkspaceProps, SubjectSelection } from "@/workbench/types";
import type { TopologyProperty } from "@/lib/types";
import { logicalTypeName } from "@/lib/expressions";
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import {
  componentMeaning,
  graphMeaning,
  propertyMeaning,
} from "@/shared/design/meaning";
import { effectiveLicenseForGraph, effectiveLicenseForModel } from "@/proof/license";
import { buildProof } from "@/proof/model";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import {
  Control,
  Empty,
  Label,
  Meta,
  Panel,
  PanelHeader,
  RowButton,
} from "@/shared/ui/Primitives";
import {
  FulfilmentMap,
} from "@/detail/view/FulfilmentMap";
import { cx, groupPalette, theme } from "@/shared/ui/theme";
import styles from "./topologyFeature.module.css";
import {
  ViewportAction,
  ViewportChip,
  ViewportFrame,
  ViewportNav,
} from "@/shared/ui/Viewport";
import { PanelRight } from "lucide-react";
import type {
  TopologyDetailOptions,
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
import { getTopologyUiStore, type TopologyUiStore } from "./topologyUi";

// ---------------------------------------------------------------------------
// Shared reading of the workbench contract
// ---------------------------------------------------------------------------

function topologySelection(props: WorkspaceProps): TopologySelection | undefined {
  const selection: SubjectSelection | undefined = props.state.inspection;
  if ((selection?.kind === "node" || selection?.kind === "edge") && selection.name) {
    return { kind: selection.kind, name: selection.name };
  }
  if (selection?.kind === "property" && selection.component) {
    const component = selection.component;
    const kind = props.state.index.topologyNodesByName.has(component)
      ? "node"
      : props.state.index.topologyEdgesByName.has(component)
        ? "edge"
        : undefined;
    if (kind) return { kind, name: component };
  }
  return undefined;
}

function writeSelection(
  props: WorkspaceProps,
  kind: TopologySelection["kind"],
  name: string,
): void {
  props.actions.inspect({ kind, name });
}

function clearSelection(props: WorkspaceProps): void {
  props.actions.inspect(undefined);
}

function entityComponentName(entity: TopologyEntity): string {
  return isTopologyNode(entity) ? entity.name : (entity.edgeName ?? entity.name);
}

function entityProperties(props: WorkspaceProps, entity: TopologyEntity): TopologyProperty[] {
  const name = entityComponentName(entity);
  const component = isTopologyNode(entity)
    ? props.state.index.topologyNodesByName.get(name)
    : props.state.index.topologyEdgesByName.get(name);
  return component?.properties ?? [];
}

/**
 * The Graph document has no subject of its own. Opening Detail from an
 * inspected subject explicitly creates that subject document first.
 */
function openInDetail(props: WorkspaceProps): void {
  const inspection = props.state.inspection;
  if (inspection?.kind) props.actions.openTab({ selection: inspection });
}

function propertySelection(
  entity: TopologyEntity,
  property: TopologyProperty,
): SubjectSelection {
  const component = entityComponentName(entity);
  return {
    kind: "property",
    level: "property",
    component,
    property: property.name,
    name: `${component}.${property.name}`,
  };
}

function componentSelection(entity: TopologyEntity): SubjectSelection {
  const component = entityComponentName(entity);
  if (isTopologyNode(entity)) {
    return {
      kind: "node",
      level: entity.abstract ? "abstract" : "node",
      component,
      name: component,
    };
  }
  return { kind: "edge", level: "edge", component, name: component };
}

function PropertyRows({
  props,
  entity,
  activeProperty,
  onContextMenu,
}: {
  props: WorkspaceProps;
  entity: TopologyEntity;
  activeProperty?: string;
  onContextMenu?(property: TopologyProperty, event: ReactMouseEvent): void;
}) {
  const properties = entityProperties(props, entity);
  if (!properties.length) {
    return <Empty>No properties are declared.</Empty>;
  }
  return (
    <div className="grid gap-0.5" data-testid="topology-properties">
      {properties.map((property) => (
        <RowButton
          key={property.name}
          onClick={() => props.actions.inspect(propertySelection(entity, property))}
          onContextMenu={(event) =>
            onContextMenu ? onContextMenu(property, event) : undefined
          }
          className="justify-between"
          data-active={activeProperty === property.name ? "true" : undefined}
          title={`Inspect ${entityComponentName(entity)}.${property.name}`}
        >
          <span className="truncate font-mono text-[length:var(--text-base)] text-text">
            {property.name}
          </span>
          <Meta>{logicalTypeName(property.logical_type)}</Meta>
        </RowButton>
      ))}
    </div>
  );
}

function useTopologyModel(props: WorkspaceProps): TopologyGraphModel {
  const { snapshot, index } = props.state;
  return useMemo(() => topologyModelFor(snapshot, index), [snapshot, index]);
}

function useTopologyUi(snapshot: string): readonly [ReturnType<TopologyUiStore["getState"]>, TopologyUiStore] {
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
// Shared visual vocabulary
// ---------------------------------------------------------------------------

function nodeRadius(node: TopologyNodeModel): number {
  return Math.max(5, Math.min(24, 4.2 + Math.sqrt(Math.max(1, node.degree)) * 2.4));
}

function clusterColors(categories: string[]): Map<string, string> {
  return new Map(
    [...new Set(categories)]
      .sort()
      .map((category, index) => [
        category,
        groupPalette[index % groupPalette.length],
      ]),
  );
}

interface BoundingCircle {
  x: number;
  y: number;
  r: number;
}

function circleContains(
  circle: BoundingCircle,
  point: [number, number],
): boolean {
  return (
    Math.hypot(point[0] - circle.x, point[1] - circle.y) <= circle.r + 1e-6
  );
}

function circumcircle(
  a: [number, number],
  b: [number, number],
  c: [number, number],
): BoundingCircle | null {
  const ax = b[0] - a[0];
  const ay = b[1] - a[1];
  const bx = c[0] - a[0];
  const by = c[1] - a[1];
  const denominator = 2 * (ax * by - ay * bx);
  if (Math.abs(denominator) < 1e-9) return null;
  const ux =
    (by * (ax * ax + ay * ay) - ay * (bx * bx + by * by)) / denominator;
  const uy =
    (ax * (bx * bx + by * by) - bx * (ax * ax + ay * ay)) / denominator;
  return { x: a[0] + ux, y: a[1] + uy, r: Math.hypot(ux, uy) };
}

/** The smallest circle that bounds a set of node centres. */
function minimumEnclosingCircle(
  points: Array<[number, number]>,
): BoundingCircle | null {
  let circle: BoundingCircle | null = null;
  for (let i = 0; i < points.length; i += 1) {
    const point = points[i];
    if (circle && circleContains(circle, point)) continue;
    circle = { x: point[0], y: point[1], r: 0 };
    for (let j = 0; j < i; j += 1) {
      const inner = points[j];
      if (circleContains(circle, inner)) continue;
      circle = {
        x: (point[0] + inner[0]) / 2,
        y: (point[1] + inner[1]) / 2,
        r: Math.hypot(point[0] - inner[0], point[1] - inner[1]) / 2,
      };
      for (let k = 0; k < j; k += 1) {
        const third = points[k];
        if (circleContains(circle, third)) continue;
        circle = circumcircle(point, inner, third) ?? circle;
      }
    }
  }
  return circle;
}

function nodeFill(
  node: TopologyNodeModel,
  colors: Map<string, string>,
): string {
  return node.abstract
    ? theme.asset
    : colors.get(node.category) ?? theme.source;
}

function pointerPosition(
  container: HTMLElement | null,
  event: ReactMouseEvent,
): { x: number; y: number } | undefined {
  const rect = container?.getBoundingClientRect();
  if (!rect) return undefined;
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function semanticsSummary(entity: TopologyEntity): string {
  const { semantics } = entity;
  if (!semantics.present) return "meaning omitted";
  const parts: string[] = [];
  if (semantics.claimCount) {
    parts.push(
      `${semantics.claimCount} claim${semantics.claimCount === 1 ? "" : "s"}`,
    );
  }
  if (semantics.purposePresent) {
    parts.push("purpose");
  }
  if (semantics.limitationCount) {
    parts.push(
      `${semantics.limitationCount} limitation${
        semantics.limitationCount === 1 ? "" : "s"
      }`,
    );
  }
  return parts.join(" · ");
}

function entityKindLabel(entity: TopologyEntity): string {
  if (entity.kind === "node") return entity.abstract ? "abstract node" : "node";
  return entity.kind === "containment" ? "containment" : "relation";
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function FilterButton({
  pressed,
  onClick,
  children,
  title,
}: {
  pressed: boolean;
  onClick: () => void;
  children: ReactNode;
  title?: string;
}) {
  return (
    <Control
      aria-pressed={pressed}
      onClick={onClick}
      title={title}
      className={cx(
        pressed
          ? "border-accent/70 bg-accent/15 text-accent-strong"
          : "bg-panel-soft/40",
      )}
    >
      <span>{children}</span>
    </Control>
  );
}

function FilterGroup({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <Label className="block">{label}</Label>
      <div className="flex flex-wrap gap-1">{children}</div>
    </div>
  );
}

function LegendRow({
  color,
  label,
  dashed,
}: {
  color: string;
  label: string;
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
      <span className="min-w-0 flex-1 truncate text-[length:var(--text-base)] text-muted">
        {label}
      </span>
    </div>
  );
}

export function TopologySidebar(props: WorkspaceProps): JSX.Element {
  const model = useTopologyModel(props);
  const [ui, store] = useTopologyUi(props.state.snapshot.name);
  const visible = useMemo(
    () => applyTopologyFilters(model, ui.filters, ui.detail),
    [model, ui.filters, ui.detail],
  );
  const filters = ui.filters;
  const detail = ui.detail;
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
    store.requestFit();
  };

  const patchDetail = (patch: Partial<TopologyDetailOptions>) => {
    store.setDetail({ ...detail, ...patch });
    if ("containment" in patch || "edges" in patch) store.requestFit();
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-panel">

      <div className="thin-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-2">
        <section className="space-y-2" aria-label="Topology filters">
          <FilterGroup label="Kind">
            <FilterButton
              pressed={filters.kinds.node}
              onClick={() => patchFilters({ kinds: { node: !filters.kinds.node } })}
              title="Show or hide topology node components"
            >
              Nodes
            </FilterButton>
            <FilterButton
              pressed={filters.kinds.edge}
              onClick={() => patchFilters({ kinds: { edge: !filters.kinds.edge } })}
              title="Show or hide topology edge components as relation links"
            >
              Relations
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Abstract">
            <FilterButton
              pressed={filters.abstract === "all"}
              onClick={() => patchFilters({ abstract: "all" })}
            >
              All
            </FilterButton>
            <FilterButton
              pressed={filters.abstract === "concrete"}
              onClick={() => patchFilters({ abstract: "concrete" })}
            >
              Concrete
            </FilterButton>
            <FilterButton
              pressed={filters.abstract === "abstract"}
              onClick={() => patchFilters({ abstract: "abstract" })}
            >
              Abstract
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Meaning">
            <FilterButton
              pressed={filters.semantics === "all"}
              onClick={() => patchFilters({ semantics: "all" })}
            >
              All
            </FilterButton>
            <FilterButton
              pressed={filters.semantics === "present"}
              onClick={() => patchFilters({ semantics: "present" })}
            >
              Present
            </FilterButton>
            <FilterButton
              pressed={filters.semantics === "missing"}
              onClick={() => patchFilters({ semantics: "missing" })}
            >
              Missing
            </FilterButton>
          </FilterGroup>
        </section>

        <section
          className="space-y-2 border-t border-line-soft pt-2"
          aria-label="Topology detail"
        >
          <FilterGroup label="Labels">
            <FilterButton
              pressed={detail.labels === "off"}
              onClick={() => patchDetail({ labels: "off" })}
              title="Hide node labels"
            >
              Off
            </FilterButton>
            <FilterButton
              pressed={detail.labels === "hubs"}
              onClick={() => patchDetail({ labels: "hubs" })}
              title="Label only the busiest nodes"
            >
              Hubs
            </FilterButton>
            <FilterButton
              pressed={detail.labels === "all"}
              onClick={() => patchDetail({ labels: "all" })}
              title="Label every visible node"
            >
              All
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Show">
            <FilterButton
              pressed={detail.edgeLabels}
              onClick={() => patchDetail({ edgeLabels: !detail.edgeLabels })}
              title="Show edge labels on relation links"
            >
              Edge labels
            </FilterButton>
            <FilterButton
              pressed={detail.containment}
              onClick={() => patchDetail({ containment: !detail.containment })}
              title="Show child to parent category containment links"
            >
              Containment
            </FilterButton>
            <FilterButton
              pressed={detail.semantics}
              onClick={() => patchDetail({ semantics: !detail.semantics })}
              title="Mark nodes and edges that carry meaning"
            >
              Meaning
            </FilterButton>
            <FilterButton
              pressed={detail.properties}
              onClick={() => patchDetail({ properties: !detail.properties })}
              title="Show property counts on nodes"
            >
              Properties
            </FilterButton>
            <FilterButton
              pressed={detail.clusters}
              onClick={() => patchDetail({ clusters: !detail.clusters })}
              title="Draw a frame around each graph category"
            >
              Clusters
            </FilterButton>
          </FilterGroup>

          <FilterGroup label="Edges">
            <FilterButton
              pressed={detail.edges === "off"}
              onClick={() => patchDetail({ edges: "off" })}
              title="Hide relation links"
            >
              Off
            </FilterButton>
            <FilterButton
              pressed={detail.edges === "relations"}
              onClick={() => patchDetail({ edges: "relations" })}
              title="Draw relation links"
            >
              Relations
            </FilterButton>
          </FilterGroup>
        </section>

        <section
          className="space-y-1.5 border-t border-line-soft pt-2"
          aria-label="Topology legend"
        >
          <Label className="block">Legend</Label>
          <LegendRow
            color={theme.source}
            label="Concrete node"
          />
          <LegendRow
            color={theme.asset}
            label="Abstract category"
            dashed
          />
          <LegendRow
            color={theme.edge}
            label="Relation edge"
          />
          <LegendRow
            color={theme.lineStrong}
            label="Category containment"
            dashed
          />
          {detail.semantics ? (
            <LegendRow
              color={theme.accent}
              label="Meaning present"
            />
          ) : null}
        </section>

        <section
          className="space-y-1.5 border-t border-line-soft pt-2"
          aria-label="Topology layout"
        >
          <Label className="block">Layout</Label>
          <div className="flex flex-wrap gap-1">
            <button
              type="button"
              onClick={() => store.requestFit()}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[length:var(--text-base)] text-muted hover:border-line-strong hover:text-text"
              title="Fit every visible node and link in the editor"
            >
              Fit
            </button>
            <button
              type="button"
              onClick={() => store.requestZoom(1 / 1.25)}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[length:var(--text-base)] text-muted hover:border-line-strong hover:text-text"
              title="Zoom out"
              aria-label="Zoom out"
            >
              −
            </button>
            <button
              type="button"
              onClick={() => store.requestZoom(1.25)}
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[length:var(--text-base)] text-muted hover:border-line-strong hover:text-text"
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
                "inline-flex min-h-6 items-center border px-2 font-mono text-[length:var(--text-base)]",
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
              className="inline-flex min-h-6 items-center border border-line-soft bg-panel-soft/40 px-2 font-mono text-[length:var(--text-base)] text-muted hover:border-line-strong hover:text-text"
              title="Clear filters, detail and pinned positions, then fit the graph"
            >
              Reset
            </button>
          </div>
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
  const radius = 240 + Math.min(300, nodes.length * 2.4);
  return new Map(
    categories.map((category, index) => {
      const angle =
        (index / Math.max(1, categories.length)) * Math.PI * 2 - Math.PI / 2;
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
  const sourceRadius = nodeRadius(source.model) + 0.75;
  const targetRadius = nodeRadius(target.model) + 0.75;
  const sourceX = source.x ?? 0;
  const sourceY = source.y ?? 0;
  const targetX = target.x ?? 0;
  const targetY = target.y ?? 0;
  if (source.id === target.id) {
    // A self-loop is a teardrop beside the node, not a ring around it: a ring
    // reads as a badge and hides the node's own state.
    const radius = sourceRadius + 3;
    const lift = radius * 0.7;
    return {
      path: `M ${sourceX + lift} ${sourceY - lift} C ${
        sourceX + radius * 2.5
      } ${sourceY - radius * 1.15}, ${sourceX + radius * 2.5} ${
        sourceY + radius * 1.15
      }, ${sourceX + lift} ${sourceY + lift}`,
      x: sourceX + lift,
      y: sourceY + lift,
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

export function TopologyEditor(props: WorkspaceProps): JSX.Element {
  const model = useTopologyModel(props);
  const [ui, store] = useTopologyUi(props.state.snapshot.name);
  const selection = topologySelection(props);
  const visible = useMemo(
    () => applyTopologyFilters(model, ui.filters, ui.detail),
    [model, ui.filters, ui.detail],
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
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        selection: SubjectSelection;
        label: string;
      }
    | undefined
  >(undefined);

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
    const nodes: SimNode[] = visible.nodes.map((node, index) => {
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
    const links: SimLink[] = visible.links.map((link) => ({
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
          .distance((link) => (link.model.kind === "containment" ? 72 : 92))
          .strength((link) => (link.model.kind === "containment" ? 0.5 : 0.11)),
      )
      .force("charge", d3.forceManyBody<SimNode>().strength(-190))
      .force("center", d3.forceCenter<SimNode>(0, 0))
      .force(
        "collide",
        d3.forceCollide<SimNode>().radius((node) => nodeRadius(node.model) + 5),
      )
      .force(
        "x",
        d3
          .forceX<SimNode>((node) => anchors.get(node.model.category)?.x ?? 0)
          .strength(0.26),
      )
      .force(
        "y",
        d3
          .forceY<SimNode>((node) => anchors.get(node.model.category)?.y ?? 0)
          .strength(0.26),
      )
      .alphaDecay(0.05)
      .velocityDecay(0.36)
      // A design map must open in the same arrangement on every load.
      .randomSource(d3.randomLcg(0.42));

    // Settle before the first paint. The graph is a static design map: an
    // animated mount would drift after the initial fit and make the viewport
    // land off-centre.
    simulation.stop();
    for (let step = 0; step < 260; step += 1) simulation.tick();
    simulation.alpha(0).stop();

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
  }, [visible]);

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
    // The inspector is an overlay, so the graph is fitted into the canvas that
    // remains visible beside it instead of underneath it.
    const left = 56;
    const right = inspectorOpen ? 352 : 56;
    const top = 56;
    const bottom = 56;
    const viewWidth = Math.max(120, width - left - right);
    const viewHeight = Math.max(120, height - top - bottom);
    const boundsWidth = Math.max(1, maxX - minX);
    const boundsHeight = Math.max(1, maxY - minY);
    const k = Math.max(
      0.15,
      Math.min(2.4, Math.min(viewWidth / boundsWidth, viewHeight / boundsHeight)),
    );
    const tx = left + viewWidth / 2 - ((minX + maxX) / 2) * k;
    const ty = top + viewHeight / 2 - ((minY + maxY) / 2) * k;
    d3.select(svg).call(
      behavior.transform,
      d3.zoomIdentity.translate(tx, ty).scale(k),
    );
  }, [inspectorOpen, model.nodes, size.height, size.width, visible.nodes]);

  const fitRef = useRef(fitGraph);
  useEffect(() => {
    fitRef.current = fitGraph;
  }, [fitGraph]);

  // Initial fit once the simulation has positions and the editor has a size.
  // Quantising the size keeps a live window drag from refitting on every pixel
  // while still fitting after a side-bar or window resize.
  useEffect(() => {
    if (!size.width || !size.height) return;
    const fitKey = `${model.graphKey}:${Math.round(size.width / 40)}x${Math.round(
      size.height / 40,
    )}:${inspectorOpen}`;
    if (lastFitRef.current === fitKey) return;
    lastFitRef.current = fitKey;
    const frame = window.requestAnimationFrame(() => fitRef.current());
    return () => window.cancelAnimationFrame(frame);
  }, [inspectorOpen, model.graphKey, size.height, size.width]);

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
          if (dragMovedRef.current) {
            node.fx = node.x;
            node.fy = node.y;
            store.setPosition(node.id, { x: node.x ?? 0, y: node.y ?? 0 });
          }
        } else {
          node.fx = null;
          node.fy = null;
          if (dragMovedRef.current) simulation.alpha(0.12).restart();
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
    if (ui.detail.labels === "off") return labels;
    if (ui.detail.labels === "all") {
      for (const node of visible.nodes) labels.add(node.id);
      return labels;
    }
    const ranked = [...visible.nodes].sort(
      (left, right) =>
        right.degree - left.degree || left.name.localeCompare(right.name),
    );
    const hubCount = Math.max(
      3,
      Math.min(10, Math.ceil(visible.nodes.length * 0.12)),
    );
    for (const node of ranked.slice(0, hubCount)) labels.add(node.id);
    return labels;
  }, [ui.detail.labels, visible.nodes]);

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
    // Hub labels yield to node circles as well as to other labels; "all" only
    // resolves label-label collisions so the explicit detail request stays
    // readable instead of turning into a wall of text.
    const checkNodeOverlap = ui.detail.labels !== "all";
    const nodeBoxes = visible.nodes
      .map((node) => {
        const sim = simById.get(node.id);
        if (!sim) return undefined;
        const radius = nodeRadius(node);
        const x = sim.x ?? 0;
        const y = sim.y ?? 0;
        return {
          id: node.id,
          left: x - radius,
          right: x + radius,
          top: y - radius,
          bottom: y + radius,
        };
      })
      .filter((box) => box !== undefined);
    const intersects = (
      left: { left: number; right: number; top: number; bottom: number },
      right: { left: number; right: number; top: number; bottom: number },
    ) =>
      !(
        left.right < right.left ||
        left.left > right.right ||
        left.bottom < right.top ||
        left.top > right.bottom
      );
    const visibleLabels = new Set<string>();
    for (const node of candidates) {
      const sim = simById.get(node.id);
      if (!sim) continue;
      const radius = nodeRadius(node);
      const width = Math.max(16, node.label.length * 6.2 + 8);
      const x = sim.x ?? 0;
      const y = sim.y ?? 0;
      const box = {
        left: x - width / 2,
        right: x + width / 2,
        top: y + radius + 2,
        bottom: y + radius + 16,
      };
      const overlapsLabel = boxes.some((other) => intersects(box, other));
      const overlapsNode =
        checkNodeOverlap &&
        nodeBoxes.some(
          (other) => other.id !== node.id && intersects(box, other),
        );
      if ((overlapsLabel || overlapsNode) && !forced.has(node.id)) continue;
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

  const openMenu = (
    event: ReactMouseEvent,
    selection: SubjectSelection,
    label: string,
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setMenu({ x: event.clientX, y: event.clientY, selection, label });
  };

  const linkSelection = (link: TopologyLinkModel): SubjectSelection => {
    if (link.kind === "containment") {
      const node = model.nodeById.get(link.target);
      return {
        kind: "node",
        level: node?.abstract ? "abstract" : "node",
        component: link.targetName,
        name: link.targetName,
      };
    }
    const component = link.edgeName ?? link.name;
    return { kind: "edge", level: "edge", component, name: component };
  };

  const showNodeMarkers = ui.filters.kinds.node;
  const visibleCount = visible.nodes.length + visible.links.length;

  const colors = clusterColors(visible.nodes.map((node) => node.category));

  // Category frames sit behind the links and follow the simulation, so the
  // hairball reads as a few named groups rather than one undifferentiated
  // cloud. A frame is drawn only when two or more visible nodes share it.
  const clusterFrames: Array<{
    category: string;
    count: number;
    cx: number;
    cy: number;
    r: number;
    labelX: number;
    labelY: number;
  }> = [];
  if (ui.detail.clusters) {
    const frames = new Map<
      string,
      {
        count: number;
        points: Array<[number, number, number]>;
        minX: number;
        minY: number;
      }
    >();
    for (const node of visible.nodes) {
      const sim = simById.get(node.id);
      if (!sim) continue;
      const radius = nodeRadius(node) + 10;
      const x = sim.x ?? 0;
      const y = sim.y ?? 0;
      const frame = frames.get(node.category) ?? {
        count: 0,
        points: [],
        minX: Number.POSITIVE_INFINITY,
        minY: Number.POSITIVE_INFINITY,
      };
      frame.count += 1;
      frame.minX = Math.min(frame.minX, x - radius);
      frame.minY = Math.min(frame.minY, y - radius);
      frame.points.push([x, y, radius]);
      frames.set(node.category, frame);
    }
    for (const [category, frame] of frames) {
      if (frame.count < 2) continue;
      const centre = minimumEnclosingCircle(
        frame.points.map(([x, y]) => [x, y]),
      ) ?? { x: 0, y: 0, r: 0 };
      const nodeRadiusMax = Math.max(
        ...frame.points.map(([, , radius]) => radius),
      );
      const r = centre.r + nodeRadiusMax + 8;
      clusterFrames.push({
        category,
        count: frame.count,
        cx: centre.x,
        cy: centre.y,
        r,
        labelX: frame.minX - 6,
        labelY: frame.minY - 28,
      });
    }
  }

  const graphLicense = effectiveLicenseForGraph(props.state.index);

  return (
    <ViewportFrame
      concept="graph"
      kicker="Graph"
      title={props.state.index.graphDeclaration?.name ?? "Graph"}
      facts={[
        { label: "Nodes", value: `${model.stats.nodes}` },
        { label: "Edges", value: `${model.stats.edgeLinks}` },
        { label: "Meaning", value: `${model.stats.semantics}` },
        { label: "License", value: graphLicense.value },
      ]}
      testId="topology-editor"
      ariaLabel="Topology force graph"
      bodyRef={containerRef}
      bodyClassName="select-none"
      actions={
        <ViewportAction
          active={inspectorOpen}
          onClick={() => setInspectorOpen((open) => !open)}
          aria-pressed={inspectorOpen}
          aria-label={inspectorOpen ? "Close inspector" : "Open inspector"}
          title={inspectorOpen ? "Close inspector" : "Open inspector"}
          data-testid="topology-open-inspector"
        >
          <PanelRight aria-hidden className="size-3" />
          Inspect
        </ViewportAction>
      }
      nav={
        <ViewportNav
          zoom={zoomK}
          onZoomOut={() => zoomBy(1 / 1.25)}
          onZoomIn={() => zoomBy(1.25)}
          onFit={() => fitRef.current()}
          label="graph"
        />
      }
    >
      <svg
        ref={svgRef}
        data-testid="topology-canvas"
        className="block h-full w-full touch-none cursor-grab select-none"
        role="img"
        aria-label={`Topology force graph with ${visible.nodes.length} nodes and ${visible.links.length} links`}
        onClick={() => {
          if (suppressClickRef.current) return;
          clearSelection(props);
        }}
      >
        <defs>
          <pattern id="topology-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.65" fill={theme.lineSoft} opacity="0.7" />
          </pattern>
          <pattern id="topology-grid-major" width="120" height="120" patternUnits="userSpaceOnUse">
            <path d="M 120 0 L 0 0 0 120" fill="none" stroke={theme.lineSoft} strokeWidth="0.6" opacity="0.5" />
          </pattern>
          <marker
            id="topology-arrow"
            viewBox="0 -4 8 8"
            refX="8"
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
            refX="8"
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
            refX="8"
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
            refX="8"
            refY="0"
            markerWidth="4"
            markerHeight="4"
            orient="auto"
          >
            <path d="M0,-4 L8,0 L0,4" fill={theme.lineStrong} />
          </marker>
        </defs>

        <rect width="100%" height="100%" fill="url(#topology-grid)" pointerEvents="none" />
        <rect width="100%" height="100%" fill="url(#topology-grid-major)" pointerEvents="none" />

        <g ref={sceneRef}>
          {clusterFrames.length ? (
            <g data-topology-clusters pointerEvents="none">
              {clusterFrames.map((frame) => (
                <g key={frame.category}>
                  <circle
                    cx={frame.cx}
                    cy={frame.cy}
                    r={frame.r}
                    fill={colors.get(frame.category) ?? theme.lineStrong}
                    fillOpacity={0.04}
                    stroke={colors.get(frame.category) ?? theme.lineStrong}
                    strokeOpacity={0.35}
                    strokeWidth={0.9}
                    strokeDasharray="2 5"
                  />
                  <text
                    x={frame.labelX}
                    y={frame.labelY}
                    fill={theme.faint}
                    fontSize="var(--text-micro)"
                    fontFamily="var(--font-sans)"
                    letterSpacing="0.08em"
                    className="select-none"
                  >
                    {frame.category.toUpperCase()} · {frame.count}
                  </text>
                </g>
              ))}
            </g>
          ) : null}
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
                      ? 0.75
                      : 0.32;
              const markerEnd = selectedNodeName && incident ? undefined : marker;
              const midX = ((source.x ?? 0) + (target.x ?? 0)) / 2;
              const midY = ((source.y ?? 0) + (target.y ?? 0)) / 2;
              return (
                <g
                  key={link.id}
                  className="transition-opacity duration-150"
                  onContextMenu={(event) =>
                    openMenu(
                      event,
                      linkSelection(link),
                      link.edgeName ?? link.name,
                    )
                  }
                >
                  <path
                    d={geometry.path}
                    fill="none"
                    stroke={tone}
                    strokeWidth={selected ? 2.6 : hovered || incident ? 1.8 : 1}
                    strokeOpacity={opacity}
                    strokeDasharray={link.kind === "containment" ? "4 3" : undefined}
                    markerEnd={markerEnd}
                    vectorEffect="non-scaling-stroke"
                    pointerEvents="none"
                  />
                  {ui.detail.edgeLabels ? (
                    <text
                      x={midX}
                      y={midY - 4}
                      textAnchor="middle"
                      fill={selected ? theme.selection : theme.muted}
                      fontSize="var(--text-micro)"
                      fontFamily="var(--font-mono)"
                      stroke={theme.page}
                      strokeWidth={3}
                      strokeLinejoin="round"
                      paintOrder="stroke"
                      pointerEvents="none"
                    >
                      {link.label}
                    </text>
                  ) : null}
                  {ui.detail.semantics && link.hasSemantics ? (
                    <circle
                      cx={midX}
                      cy={midY}
                      r={2.2}
                      fill={theme.accent}
                      stroke={theme.page}
                      strokeWidth={0.8}
                      pointerEvents="none"
                    />
                  ) : null}
                  <path
                    data-topology-link={link.kind === "edge" ? link.edgeName : link.name}
                    data-topology-link-kind={link.kind}
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
                      {`${link.label} · ${link.sourceName} → ${link.targetName}`}
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
                  const base = nodeFill(node, colors);
                  const ring = selected
                    ? theme.selection
                    : hovered || focused
                      ? theme.accentStrong
                      : base;
                  const showLabel = labelIds.has(node.id);
                  return (
                    <g
                      key={node.id}
                      className="transition-opacity duration-150"
                      data-topology-node-id={node.id}
                      data-topology-node={node.name}
                      transform={`translate(${sim.x ?? 0} ${sim.y ?? 0})`}
                      opacity={dim ? 0.2 : 1}
                      tabIndex={0}
                      role="button"
                      aria-pressed={selected}
                      aria-label={`${node.label}, ${node.abstract ? "abstract category" : "node"}, ${node.category}, ${node.degree} links, ${node.properties} properties`}
                      onClick={(event) => {
                        event.stopPropagation();
                        selectNode(node);
                      }}
                      onDoubleClick={(event) => {
                        event.stopPropagation();
                        selectNode(node);
                        focusNode(sim);
                      }}
                      onContextMenu={(event) =>
                        openMenu(event, componentSelection(node), node.name)
                      }
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
                        } properties`}
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
                      {ui.detail.semantics && node.hasSemantics ? (
                        <circle
                          cx={radius * 0.72}
                          cy={-radius * 0.72}
                          r={2.4}
                          fill={theme.accent}
                          stroke={theme.page}
                          strokeWidth={0.8}
                          pointerEvents="none"
                        />
                      ) : null}
                      {ui.detail.properties ? (
                        <text
                          x={-radius - 3}
                          y={-radius - 2}
                          textAnchor="end"
                          fill={theme.faint}
                          fontSize="var(--text-micro)"
                          fontFamily="var(--font-mono)"
                          stroke={theme.page}
                          strokeWidth={3}
                          strokeLinejoin="round"
                          paintOrder="stroke"
                          className="pointer-events-none select-none"
                        >
                          {`${node.properties}p`}
                        </text>
                      ) : null}
                      {showLabel ? (
                        (() => {
                          const label = node.label;
                          const width = Math.max(22, label.length * 5.6 + 10);
                          return (
                            <g className="pointer-events-none select-none">
                              <rect
                                x={-width / 2}
                                y={radius + 3}
                                width={width}
                                height={14}
                                rx={2}
                                fill={theme.page}
                                fillOpacity={0.9}
                                stroke={
                                  selected
                                    ? theme.selection
                                    : theme.lineSoft
                                }
                                strokeWidth={0.7}
                              />
                              <text
                                y={radius + 13}
                                textAnchor="middle"
                                fill={
                                  selected
                                    ? theme.selection
                                    : hovered || focused
                                      ? theme.text
                                      : theme.muted
                                }
                                fontSize="var(--text-caption)"
                                fontFamily="var(--font-sans)"
                                letterSpacing="0.02em"
                              >
                                {label}
                              </text>
                            </g>
                          );
                        })()
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
          <ViewportChip className="pointer-events-auto text-selection-strong">
            selected · {selection?.name}
          </ViewportChip>
        ) : null}
        {ui.pinned ? (
          <ViewportChip className="pointer-events-auto border-selection/60 bg-selection/10 text-selection-strong">
            positions pinned
          </ViewportChip>
        ) : null}
      </div>

      {visibleCount === 0 ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="border border-line-soft bg-panel/95 px-3 py-2 font-mono text-[length:var(--text-xl)] text-muted">
            No topology entities match these filters.
          </p>
        </div>
      ) : null}

      {inspectorOpen ? (
        <TopologyInspector props={props} onClose={() => setInspectorOpen(false)} />
      ) : null}

      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          label={menu.label}
          items={[
            {
              label: "Go to Detail",
              hint: "Open document",
              onSelect: () =>
                props.actions.openTab({ selection: menu.selection }),
            },
          ]}
          onClose={() => setMenu(undefined)}
        />
      ) : null}

      {hover && hoverEntity ? (
        <div
          className="pointer-events-none absolute z-30 w-[270px] overflow-hidden rounded-[var(--radius-lg)] border border-line-soft bg-panel/98 shadow-lg"
          style={{ left: hover.x + 14, top: hover.y + 14 }}
        >
          <p className="border-b border-line-soft px-2 py-1 font-mono text-[length:var(--text-base)] break-words text-accent-strong">
            {hoverEntity.label}
            {hoverEntity.label !== hoverEntity.name ? (
              <span className="text-faint"> · {hoverEntity.name}</span>
            ) : null}
          </p>
          <div className="space-y-0.5 px-2 py-1 font-mono text-[length:var(--text-sm)] text-muted">
            {hoverEntity.kind === "node" ? (
              <>
                <p>
                  node · {hoverEntity.abstract ? "abstract" : "concrete"} ·{" "}
                  {hoverEntity.category}
                </p>
                <p>{hoverEntity.degree} links</p>
                {ui.detail.properties ? (
                  <p>{hoverEntity.properties} properties</p>
                ) : null}
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
            {ui.detail.semantics ? (
              <p>semantics {semanticsSummary(hoverEntity)}</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </ViewportFrame>
  );
}

// ---------------------------------------------------------------------------
// Floating Graph inspector: the selected design entity
// ---------------------------------------------------------------------------

function SummaryField({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div className="grid grid-cols-[minmax(0,max-content)_minmax(0,1fr)] items-baseline gap-3">
      <span className="whitespace-nowrap text-[length:var(--text-sm)] tracking-[0.06em] text-faint uppercase">
        {label}
      </span>
      <span
        className="min-w-0 truncate font-mono text-[length:var(--text-base)] text-text"
        title={String(value)}
      >
        {value}
      </span>
    </div>
  );
}

function inspectorMeaning(
  props: WorkspaceProps,
  entity: TopologyEntity,
  activeProperty?: string,
): {
  claims: ReturnType<typeof propertyMeaning>["claims"];
  limitations: ReturnType<typeof propertyMeaning>["limitations"];
  purpose?: string;
  frames?: ReturnType<typeof propertyMeaning>["frames"];
} {
  if (activeProperty) {
    return propertyMeaning(
      props.state.index,
      isTopologyNode(entity) ? "node" : "edge",
      entityComponentName(entity),
      activeProperty,
    );
  }
  return isTopologyNode(entity)
    ? componentMeaning(props.state.index, "node", entity.name)
    : componentMeaning(props.state.index, "edge", entityComponentName(entity));
}

export function TopologyInspector({
  props,
  onClose,
}: {
  props: WorkspaceProps;
  onClose(): void;
}) {
  const model = useTopologyModel(props);
  const selection = topologySelection(props);
  const entity = findTopologyEntity(model, selection);
  const raw = props.state.inspection;
  const activeProperty = raw?.kind === "property" ? raw.property : undefined;
  const meaning = entity ? inspectorMeaning(props, entity, activeProperty) : undefined;
  const graphSemantics = graphMeaning(props.state.index);
  const graphLicense = effectiveLicenseForGraph(props.state.index);
  const entityKind = entity
    ? isTopologyNode(entity)
      ? "node"
      : "edge"
    : undefined;
  const entityComponent = entity
    ? isTopologyNode(entity)
      ? entity.name
      : entityComponentName(entity)
    : undefined;
  const entityLicense =
    entity && entityKind && entityComponent
      ? effectiveLicenseForModel(
          props.state.index,
          buildProof(
            props.state.index,
            activeProperty
              ? {
                  level: "property",
                  kind: entityKind,
                  component: entityComponent,
                  property: activeProperty,
                }
              : {
                  level: entityKind,
                  kind: entityKind,
                  component: entityComponent,
                },
          ),
        )
      : undefined;
  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        selection: SubjectSelection;
        label: string;
      }
    | undefined
  >(undefined);


  return (
    <Panel
      as="aside"
      className={cx(
        styles.inspector,
        "absolute top-0 right-0 bottom-0 z-20 flex w-[336px] flex-col rounded-none border-0 border-l border-line",
      )}
      aria-label="Graph selection inspector"
      data-testid="topology-inspector"
    >
      <PanelHeader as="header" className="flex-none justify-between">
        <Label className="text-text">Inspect</Label>
        <button
          type="button"
          className="text-[length:var(--text-base)] text-faint hover:text-text"
          onClick={onClose}
          aria-label="Close inspector"
          title="Close inspector"
        >
          ×
        </button>
      </PanelHeader>

      {!entity ? (
        <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto px-3 py-2">
          <p className="mb-1 text-[length:var(--text-sm)] font-semibold tracking-[0.08em] text-faint uppercase">
            Graph overview
          </p>
          <div className="mb-2 grid grid-cols-2 gap-x-3 gap-y-1">
            <SummaryField label="Nodes" value={model.stats.nodes} />
            <SummaryField label="Abstract" value={model.stats.abstractNodes} />
            <SummaryField label="Relations" value={model.stats.edgeLinks} />
            <SummaryField label="Meaning" value={model.stats.semantics} />
            <div className="col-span-2">
              <SummaryField label="License" value={graphLicense.value} />
            </div>
          </div>
          <DesignMeaning
            claims={graphSemantics.claims}
            limitations={graphSemantics.limitations}
            purpose={graphSemantics.purpose}
            frames={graphSemantics.frames}
            emptyText="No graph purpose is attached."
          />
        </div>
      ) : (
        <div className="thin-scrollbar min-h-0 flex-1 space-y-3 overflow-y-auto px-3 py-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate font-mono text-[length:var(--text-xl)] text-accent-strong">
                {activeProperty ? `${entity.name}.${activeProperty}` : entity.name}
              </p>
            </div>
            <div className="flex shrink-0 gap-1">
              <button
                type="button"
                onClick={() => openInDetail(props)}
                className="border border-accent/60 bg-accent/10 px-1.5 py-0.5 font-mono text-[length:var(--text-sm)] text-accent-strong hover:border-accent hover:text-text"
                data-testid="topology-open-detail"
              >
                Detail
              </button>
              <button
                type="button"
                onClick={() => clearSelection(props)}
                className="border border-line-soft px-1.5 py-0.5 font-mono text-[length:var(--text-sm)] text-muted hover:border-line-strong hover:text-text"
              >
                Clear
              </button>
            </div>
          </div>

          <section>
            <Label className="mb-1 block">Identity</Label>
            <div className="grid gap-1">
              <SummaryField label="Category" value={entity.category} />
              <SummaryField
                label="Effective license"
                value={entityLicense?.value ?? "Not declared"}
              />
              {isTopologyNode(entity) ? null : (
                <>
                  <SummaryField label="Source" value={entity.sourceName} />
                  <SummaryField label="Target" value={entity.targetName} />
                </>
              )}
              {activeProperty ? (
                <SummaryField label="Property" value={activeProperty} />
              ) : null}
              <SummaryField
                label="Labels"
                value={entity.labels.length ? entity.labels.join(", ") : "—"}
              />
            </div>
            {entity.description ? (
              <p className="mt-1.5 text-[length:var(--text-base)] leading-relaxed text-muted">
                {entity.description}
              </p>
            ) : null}
          </section>

          <section>
            <Label className="mb-1 block">Properties</Label>
            <PropertyRows
              props={props}
              entity={entity}
              activeProperty={activeProperty}
              onContextMenu={(property, event) => {
                const selection = propertySelection(entity, property);
                setMenu({
                  x: event.clientX,
                  y: event.clientY,
                  selection,
                  label: selection.name ?? property.name,
                });
              }}
            />
          </section>

          <section>
            <Label className="mb-1 block">Meaning</Label>
            <DesignMeaning
              claims={meaning?.claims ?? []}
              limitations={meaning?.limitations ?? []}
              purpose={meaning?.purpose}
              frames={meaning?.frames}
              emptyText={
                activeProperty
                  ? "Meaning omitted for this property."
                  : "Meaning omitted for this entity."
              }
            />
          </section>

          <section>
            <Label className="mb-1 block">Fulfilment</Label>
            <FulfilmentMap
              index={props.state.index}
              narrow
              subject={
                activeProperty
                  ? {
                      kind: "property",
                      component: entityComponent ?? entity.name,
                      property: activeProperty,
                    }
                  : {
                      kind: isTopologyNode(entity) ? "node" : "edge",
                      component: entityComponent ?? entity.name,
                    }
              }
            />
          </section>
        </div>
      )}

      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          label={menu.label}
          items={[
            {
              label: "Go to Detail",
              hint: "Open document",
              onSelect: () =>
                props.actions.openTab({ selection: menu.selection }),
            },
          ]}
          onClose={() => setMenu(undefined)}
        />
      ) : null}
    </Panel>
  );
}
