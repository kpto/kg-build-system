"use client";

import { memo, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownLeft,
  ArrowUpRight,
  ChevronRight,
  ExternalLink,
  Focus,
  Info,
  Maximize2,
  Minus,
  MousePointer2,
  Orbit,
  Plus,
  RotateCcw,
  ShieldQuestion,
} from "lucide-react";
import { AnnotationPopover } from "@/shared/ui/AnnotationPopover";
import { Field } from "@/shared/ui/Field";
import { PanelHeader } from "@/shared/ui/PanelHeader";
import { Row } from "@/shared/ui/Row";
import { Section } from "@/shared/ui/Section";
import { cx, groupPalette, severityColor, theme } from "@/shared/ui/theme";
import type {
  TopologyLinkModel,
  TopologyModel,
  TopologyNavigatorModel,
  TopologyNavigatorSection,
  TopologyNodeModel,
  TopologySelection,
} from "@/topology/model/TopologyModel";
import type { PropertyBadgeModel } from "@/topology/model/propertyBadges";

interface MapNode extends TopologyNodeModel {
  radius: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
}

interface MapLink extends TopologyLinkModel {}

interface MapGraph {
  nodes: MapNode[];
  links: MapLink[];
  byName: Map<string, MapNode>;
}

interface Viewport {
  x: number;
  y: number;
  k: number;
}

interface DragState {
  pointerId: number;
  startClientX: number;
  startClientY: number;
  startView: { x: number; y: number };
  startPan: Viewport;
  moved: boolean;
  latestView: { x: number; y: number } | undefined;
  press: { kind: "node" | "link"; name: string } | undefined;
}

interface LinkPointer {
  x: number;
  y: number;
  flipX: boolean;
  flipY: boolean;
}

interface LinkHoverState {
  link: MapLink;
  pointer: LinkPointer;
}

interface MapSceneProps {
  graph: MapGraph;
  colors: Map<string, string>;
  selected: TopologySelection | undefined;
  groupFilter: string | undefined;
  focusMode: boolean;
  onSelectNode: (name: string) => void;
  onSelectEdge: (edgeName: string) => void;
  onNodeClick: (name: string) => void;
  onLinkClick: (edgeName: string) => void;
  onLinkHover: (link: MapLink | undefined, clientX?: number, clientY?: number) => void;
}

const WIDTH = 1200;
const HEIGHT = 800;
const MIN_ZOOM = 0.35;
const MAX_ZOOM = 4;
const DRAG_THRESHOLD = 4;
const IDENTITY_VIEW: Viewport = { x: 0, y: 0, k: 1 };

const LABEL_FONT_SIZE = 10.5;
const LABEL_FONT_WEIGHT = 400;
const LABEL_Y_OFFSET = 10.5;
const LABEL_CHAR_WIDTH = 6.1;
const LABEL_BOX_HEIGHT = 12;
/** Only hubs get a permanent label; everything else labels on hover/select. */
const LABEL_MIN_DEGREE = 4;
const LABEL_MAX_AMBIENT = 18;

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

function pairKey(source: string, target: string): string {
  return source < target
    ? `${source}\u0000${target}`
    : `${target}\u0000${source}`;
}

function linkPath(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
  offset: number,
  normalX: number,
  normalY: number,
): string {
  if (Math.abs(offset) < 0.01) {
    return `M ${startX} ${startY} L ${endX} ${endY}`;
  }
  const controlX = (startX + endX) / 2 + normalX * offset * 2;
  const controlY = (startY + endY) / 2 + normalY * offset * 2;
  return `M ${startX} ${startY} Q ${controlX} ${controlY} ${endX} ${endY}`;
}

function zoomAt(viewport: Viewport, anchor: { x: number; y: number }, target: number): Viewport {
  const nextK = clamp(target, MIN_ZOOM, MAX_ZOOM);
  if (nextK === viewport.k) return viewport;
  const worldX = (anchor.x - viewport.x) / viewport.k;
  const worldY = (anchor.y - viewport.y) / viewport.k;
  return {
    x: anchor.x - worldX * nextK,
    y: anchor.y - worldY * nextK,
    k: nextK,
  };
}

function clientToView(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): { x: number; y: number } | undefined {
  const matrix = svg.getScreenCTM();
  if (!matrix) return undefined;
  const point = svg.createSVGPoint();
  point.x = clientX;
  point.y = clientY;
  const transformed = point.matrixTransform(matrix.inverse());
  return { x: transformed.x, y: transformed.y };
}

/** View-specific force layout. The model owns the graph, never its coordinates. */
function layout(model: TopologyModel): MapGraph {
  const nodes: MapNode[] = model.canvas.nodes.map((value) => ({
    ...value,
    radius: 8,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
  }));
  const byName = new Map(nodes.map((node) => [node.name, node]));
  const links: MapLink[] = model.canvas.links.map((link) => ({ ...link }));

  nodes.forEach((node, position) => {
    const angle = position * 2.399963229728653;
    const distance = 26 * Math.sqrt(position + 1);
    node.x = WIDTH / 2 + Math.cos(angle) * distance;
    node.y = HEIGHT / 2 + Math.sin(angle) * distance;
    node.radius = Math.max(
      4.5,
      Math.min(9.5, 3.2 + Math.sqrt(node.degree) * 1.35),
    );
  });

  const iterations = 620;
  for (let step = 0; step < iterations; step += 1) {
    for (let left = 0; left < nodes.length; left += 1) {
      const a = nodes[left];
      for (let right = left + 1; right < nodes.length; right += 1) {
        const b = nodes[right];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const distanceSquared = Math.max(25, dx * dx + dy * dy);
        const force = 5400 / distanceSquared;
        const distance = Math.sqrt(distanceSquared);
        const fx = (dx / distance) * force;
        const fy = (dy / distance) * force;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }
    for (const link of links) {
      const source = byName.get(link.source);
      const target = byName.get(link.target);
      if (!source || !target) continue;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const distance = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      const desired =
        96 +
        (source.degree + target.degree) * 1.6 +
        source.radius +
        target.radius;
      const force = (distance - desired) * 0.021;
      const fx = (dx / distance) * force;
      const fy = (dy / distance) * force;
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    }
    for (const node of nodes) {
      node.vx += (WIDTH / 2 - node.x) * 0.001;
      node.vy += (HEIGHT / 2 - node.y) * 0.001;
      node.vx *= 0.84;
      node.vy *= 0.84;
      node.x += node.vx;
      node.y += node.vy;
    }
  }

  const collisionPadding = 5;
  for (let pass = 0; pass < 12; pass += 1) {
    let moved = false;
    for (let left = 0; left < nodes.length; left += 1) {
      const a = nodes[left];
      for (let right = left + 1; right < nodes.length; right += 1) {
        const b = nodes[right];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const minimum = a.radius + b.radius + collisionPadding;
        const distanceSquared = dx * dx + dy * dy;
        if (distanceSquared >= minimum * minimum) continue;
        const distance = Math.sqrt(distanceSquared);
        let ux: number;
        let uy: number;
        if (distance > 0.001) {
          ux = dx / distance;
          uy = dy / distance;
        } else {
          const angle = (left + 1) * 2.399963229728653 + (right + 1) * 0.5;
          ux = Math.cos(angle);
          uy = Math.sin(angle);
        }
        const push = (minimum - distance) * 0.5;
        a.x -= ux * push;
        a.y -= uy * push;
        b.x += ux * push;
        b.y += uy * push;
        moved = true;
      }
    }
    if (!moved) break;
  }

  return { nodes, links, byName };
}

const MapScene = memo(function MapScene({
  graph,
  colors,
  selected,
  groupFilter,
  focusMode,
  onSelectNode,
  onSelectEdge,
  onNodeClick,
  onLinkClick,
  onLinkHover,
}: MapSceneProps) {
  const [hoveredNode, setHoveredNode] = useState<string | undefined>();
  const [focusedNode, setFocusedNode] = useState<string | undefined>();
  const [hoveredLink, setHoveredLink] = useState<string | undefined>();
  const [focusedLink, setFocusedLink] = useState<string | undefined>();

  const linkGeometry = useMemo(() => {
    const paths = new Map<string, string>();
    const pairs = new Map<string, MapLink[]>();
    for (const link of graph.links) {
      if (link.source === link.target) continue;
      const key = pairKey(link.source, link.target);
      const list = pairs.get(key) ?? [];
      list.push(link);
      pairs.set(key, list);
    }

    for (const [key, links] of pairs) {
      const [leftName, rightName] = key.split("\u0000");
      const left = graph.byName.get(leftName);
      const right = graph.byName.get(rightName);
      if (!left || !right) continue;

      const chordX = right.x - left.x;
      const chordY = right.y - left.y;
      const chordLength = Math.max(1, Math.hypot(chordX, chordY));
      const normalX = -chordY / chordLength;
      const normalY = chordX / chordLength;
      const ordered = [...links].sort((a, b) => a.id.localeCompare(b.id));
      const spacing =
        ordered.length <= 1 ? 0 : Math.min(20, 40 / (ordered.length - 1));

      ordered.forEach((link, index) => {
        const source = graph.byName.get(link.source);
        const target = graph.byName.get(link.target);
        if (!source || !target) return;
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const ux = dx / distance;
        const uy = dy / distance;
        const startX = source.x + ux * (source.radius + 2);
        const startY = source.y + uy * (source.radius + 2);
        const endX = target.x - ux * (target.radius + 2);
        const endY = target.y - uy * (target.radius + 2);
        const offset =
          spacing === 0 ? 0 : (index - (ordered.length - 1) / 2) * spacing;
        paths.set(
          link.id,
          linkPath(startX, startY, endX, endY, offset, normalX, normalY),
        );
      });
    }

    return paths;
  }, [graph]);

  const visibleNames = useMemo(() => {
    if (!focusMode || !selected) return undefined;
    const names = new Set<string>();
    if (selected.kind === "node") {
      names.add(selected.name);
      for (const link of graph.links) {
        if (link.source === selected.name) names.add(link.target);
        if (link.target === selected.name) names.add(link.source);
      }
    } else {
      const link = graph.links.find((candidate) => candidate.edgeName === selected.name);
      if (link) {
        names.add(link.source);
        names.add(link.target);
      }
    }
    return names;
  }, [focusMode, graph.links, selected]);

  const visibleLabels = useMemo(() => {
    const visible = new Set<string>();
    const boxes: Array<{
      left: number;
      right: number;
      top: number;
      bottom: number;
    }> = [];
    const priority: string[] = [];
    const seen = new Set<string>();

    const add = (name: string | undefined) => {
      if (!name || seen.has(name) || !graph.byName.has(name)) return;
      seen.add(name);
      priority.push(name);
    };

    if (selected?.kind === "node") add(selected.name);
    add(hoveredNode);
    add(focusedNode);
    if (selected?.kind === "node") {
      // Label only the neighbours that matter at a glance; the rest label on
      // hover. Labelling all 56 neighbours recreates the wall of text.
      for (const link of graph.links) {
        const other = link.source === selected.name ? link.target : link.target === selected.name ? link.source : undefined;
        if (!other) continue;
        const node = graph.byName.get(other);
        if (node && (node.degree >= 4 || focusedNode === other)) add(other);
      }
    }

    const rest = graph.nodes
      .filter((node) => !seen.has(node.name) && node.degree >= LABEL_MIN_DEGREE)
      .sort((a, b) => b.degree - a.degree || a.name.localeCompare(b.name))
      .slice(0, LABEL_MAX_AMBIENT);
    for (const node of rest) priority.push(node.name);

    const forced = new Set<string>();
    if (selected?.kind === "node") forced.add(selected.name);
    if (hoveredNode) forced.add(hoveredNode);
    if (focusedNode) forced.add(focusedNode);

    for (const name of priority) {
      const node = graph.byName.get(name);
      if (!node) continue;
      const width = Math.max(10, name.length * LABEL_CHAR_WIDTH) + 4;
      const labelY = node.y + node.radius + LABEL_Y_OFFSET;
      const box = {
        left: node.x - width / 2,
        right: node.x + width / 2,
        top: labelY - LABEL_BOX_HEIGHT + 3,
        bottom: labelY + 3,
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
      if (!forced.has(name) && overlaps) continue;
      boxes.push(box);
      visible.add(name);
    }

    return visible;
  }, [graph, selected, hoveredNode, focusedNode]);

  const isDimmed = (name: string, group: string): boolean => {
    if (selected?.kind === "node" && selected.name === name) return false;
    if (groupFilter && group !== groupFilter) return true;
    if (visibleNames && !visibleNames.has(name)) return true;
    return false;
  };

  return (
    <g>
      <g aria-hidden="true">
        {graph.links.map((link) => {
          const path = linkGeometry.get(link.id);
          const source = graph.byName.get(link.source);
          const target = graph.byName.get(link.target);
          if (!path || !source || !target) return null;
          const dim =
            !(selected?.kind === "edge" && selected.name === link.edgeName) &&
            (isDimmed(source.name, source.group) ||
              isDimmed(target.name, target.group));
          const hover =
            hoveredLink === link.edgeName || focusedLink === link.edgeName;
          const selectedEdge =
            selected?.kind === "edge" && selected.name === link.edgeName;
          const incidentToSelected =
            selected?.kind === "node" &&
            (selected.name === link.source || selected.name === link.target);
          const tone = selectedEdge
            ? theme.selection
            : hover
              ? theme.accent
              : theme.edge;
          const width = selectedEdge || hover
            ? 2.5
            : incidentToSelected
              ? 1.45
              : 1.25;
          const opacity = dim
            ? 0.06
            : selectedEdge || hover
              ? 0.95
              : incidentToSelected
                ? 0.8
                : 0.7;
          return (
            <g key={link.id}>
              {selectedEdge ? (
                <path
                  d={path}
                  fill="none"
                  stroke={theme.selection}
                  strokeWidth={4}
                  strokeOpacity={0.12}
                  strokeLinecap="round"
                  vectorEffect="non-scaling-stroke"
                  pointerEvents="none"
                />
              ) : null}
              <path
                d={path}
                fill="none"
                stroke={tone}
                strokeWidth={width}
                strokeOpacity={opacity}
                strokeLinecap="round"
                vectorEffect="non-scaling-stroke"
                pointerEvents="none"
              />
            </g>
          );
        })}
      </g>

      <g>
        {graph.links.map((link) => {
          const path = linkGeometry.get(link.id);
          const source = graph.byName.get(link.source);
          const target = graph.byName.get(link.target);
          if (!path || !source || !target) return null;
          return (
            <path
              key={`hit:${link.id}`}
              data-testid={`map-link-${link.edgeName}`}
              data-map-link={link.edgeName}
              d={path}
              fill="none"
              stroke="transparent"
              strokeWidth={14}
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
              pointerEvents="stroke"
              tabIndex={0}
              role="button"
              aria-label={`Relationship ${link.edgeName}, ${source.name} to ${target.name}`}
              onClick={() => onLinkClick(link.edgeName)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectEdge(link.edgeName);
                }
              }}
              onFocus={() => setFocusedLink(link.edgeName)}
              onBlur={() => setFocusedLink(undefined)}
              onMouseEnter={(event) => {
                setHoveredLink(link.edgeName);
                onLinkHover(link, event.clientX, event.clientY);
              }}
              onMouseMove={(event) => onLinkHover(link, event.clientX, event.clientY)}
              onMouseLeave={() => {
                setHoveredLink(undefined);
                onLinkHover(undefined);
              }}
            >
              <title>{`${link.edgeName}: ${source.name} → ${target.name}`}</title>
            </path>
          );
        })}
      </g>

      <g>
        {graph.nodes.map((node) => {
          const dim = isDimmed(node.name, node.group);
          const active = selected?.kind === "node" && selected.name === node.name;
          const hovered = hoveredNode === node.name || focusedNode === node.name;
          const color = colors.get(node.group) ?? theme.faint;
          const ringStroke = active
            ? theme.selection
            : hovered
              ? theme.accent
              : undefined;
          return (
            <g
              key={node.name}
              data-testid={`map-node-${node.name}`}
              data-map-node={node.name}
              transform={`translate(${node.x} ${node.y})`}
              opacity={dim ? 0.14 : 1}
              tabIndex={0}
              role="button"
              aria-pressed={active}
              aria-label={`${node.name}, ${node.group} group, ${node.degree} links${
                node.abstract ? ", abstract" : ""
              }`}
              onClick={() => onNodeClick(node.name)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelectNode(node.name);
                }
              }}
              onFocus={() => setFocusedNode(node.name)}
              onBlur={() => setFocusedNode(undefined)}
              onMouseEnter={() => setHoveredNode(node.name)}
              onMouseLeave={() => setHoveredNode(undefined)}
            >
              {active || hovered ? (
                <circle
                  r={node.radius + 2.5}
                  fill="none"
                  stroke={ringStroke}
                  strokeWidth={active ? 1.5 : 1.2}
                  vectorEffect="non-scaling-stroke"
                  pointerEvents="none"
                />
              ) : null}
              <circle
                r={node.radius}
                fill={color}
                fillOpacity={node.abstract ? 0.1 : 0.16}
                stroke={color}
                strokeWidth={1}
                strokeDasharray={node.abstract ? "2 2" : undefined}
                vectorEffect="non-scaling-stroke"
              />
              {visibleLabels.has(node.name) ? (
                <text
                  y={node.radius + LABEL_Y_OFFSET}
                  textAnchor="middle"
                  fill={
                    active
                      ? theme.selection
                      : hovered
                        ? theme.text
                        : theme.muted
                  }
                  fontSize={LABEL_FONT_SIZE}
                  fontWeight={LABEL_FONT_WEIGHT}
                  stroke={theme.page}
                  strokeWidth={2.5}
                  strokeLinejoin="round"
                  paintOrder="stroke"
                  className="pointer-events-none select-none"
                >
                  {node.name}
                </text>
              ) : null}
              <title>{`${node.name} · ${node.group} · ${node.degree} links${
                node.abstract ? " · abstract" : ""
              }`}</title>
            </g>
          );
        })}
      </g>
    </g>
  );
});

const ZoomReadout = memo(function ZoomReadout({
  levelRef,
}: {
  levelRef: { current: HTMLSpanElement | null };
}) {
  return (
    <span
      ref={levelRef}
      data-testid="map-zoom-level"
      className="w-11 border-r border-line bg-panel-soft/30 py-1 text-center font-mono text-[10px] text-muted tabular-nums"
      aria-label="Zoom 100 percent"
    >
      100%
    </span>
  );
});

const BADGE_TONE_CLASS: Record<PropertyBadgeModel["tone"], string> = {
  trace: "text-source",
  literal: "text-faint",
  fallback: "text-accent",
  multi: "text-transform",
  risk: "text-post",
  impact: "text-asset",
};

function PropertyBadges({ badges }: { badges: PropertyBadgeModel[] }) {
  return (
    <span className="flex flex-wrap items-center gap-1">
      {badges.map((badge) => (
        <span
          key={badge.id}
          className={cx(
            "inline-flex items-center gap-1 text-[10px] whitespace-nowrap",
            BADGE_TONE_CLASS[badge.tone],
          )}
          title={badge.title}
          style={badge.severity ? { color: severityColor[badge.severity] } : undefined}
        >
          <span
            aria-hidden
            className="size-1 shrink-0 rounded-full opacity-80"
            style={{
              backgroundColor: badge.severity
                ? severityColor[badge.severity]
                : "currentColor",
            }}
          />
          {badge.label}
        </span>
      ))}
    </span>
  );
}

function selectionNeighbourCount(section: TopologyNavigatorSection): number {
  return Number(section.fields?.find((field) => field.id === "links")?.value ?? 0);
}

function NavigatorSelection({
  section,
  focusMode,
  onToggleFocus,
  onReset,
}: {
  section: TopologyNavigatorSection;
  focusMode: boolean;
  onToggleFocus: () => void;
  onReset: () => void;
}) {
  const row = section.rows[0];
  const open = row?.actions?.find((action) => action.id === "open-entity");
  const review = section.actions?.find((action) => action.id === "review");
  const busiest = section.actions?.find((action) => action.id === "select-busiest");
  const neighbourCount = selectionNeighbourCount(section);

  if (row && open) {
    return (
      <>
        <Row
          as="button"
          interactive
          selected
          data-testid="map-open-explorer"
          data-selected="true"
          aria-current="true"
          onClick={() => open.run()}
          title={open.title ?? open.label}
          className="w-full"
        >
          <span className="shrink-0 font-mono text-[9px] tracking-[0.06em] text-accent-strong uppercase">
            {row.meta}
          </span>
          <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-text">
            {row.label}
          </span>
          {row.abstract ? (
            <span className="ui-row-meta">abstract</span>
          ) : null}
          <ExternalLink className="size-3 shrink-0 text-faint" aria-hidden />
        </Row>

        <div className="py-1">
          {(section.fields ?? []).map((entry) => (
            <Field key={entry.id} label={entry.label} value={entry.value} title={entry.title} />
          ))}
        </div>

        {section.description ? (
          <p className="px-2 pb-1 text-[10px] leading-relaxed text-muted text-pretty">
            {section.description}
          </p>
        ) : null}

        {section.chips?.length || section.annotations?.annotations.length ? (
          <div className="flex flex-wrap items-center gap-1 px-2 pb-1">
            {section.chips?.map((label) => (
              <span key={label} className="ui-chip text-muted">
                {label}
              </span>
            ))}
            {section.annotations?.annotations.length ? (
              <span className="ui-chip text-faint">
                {section.annotations.annotations.length} annotation
                {section.annotations.annotations.length === 1 ? "" : "s"}
              </span>
            ) : null}
          </div>
        ) : null}

        <div className="flex flex-wrap gap-1 px-2 py-1">
          {review ? (
            <button
              type="button"
              data-testid="map-review"
              data-level="control"
              onClick={() => review.run()}
              title={review.title}
              className="ui-button ui-focus-ring flex-1"
            >
              <ShieldQuestion className="size-3" aria-hidden />
              review
              {section.reviewCount ? (
                <span className="ui-row-meta">{section.reviewCount}</span>
              ) : null}
            </button>
          ) : null}
          <button
            type="button"
            data-testid="map-focus"
            data-level="control"
            aria-pressed={focusMode}
            onClick={onToggleFocus}
            className={cx(
              "ui-button ui-focus-ring flex-1",
              focusMode && "border-accent/60 bg-accent/10 text-accent-strong",
            )}
            title="Dim every other node and keep this selection and its neighbours"
          >
            <Focus className="size-3" aria-hidden />
            focus
            <span className="ui-row-meta">{neighbourCount}</span>
          </button>
          <button
            type="button"
            data-testid="map-reset"
            data-level="control"
            onClick={onReset}
            className="ui-button ui-focus-ring"
            title="Clear selection, filter and focus and fit the whole graph"
          >
            <RotateCcw className="size-3" aria-hidden />
            reset
          </button>
        </div>
      </>
    );
  }

  return (
    <div data-testid="map-empty" className="px-2 py-2">
      <p className="ui-hint">{section.empty}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {busiest ? (
          <button
            type="button"
            data-testid="map-select-busiest"
            data-level="control"
            onClick={() => busiest.run()}
            title={busiest.title}
            className="ui-button ui-focus-ring"
          >
            <MousePointer2 className="size-3" aria-hidden />
            {busiest.label}
          </button>
        ) : null}
        <button
          type="button"
          data-testid="map-reset"
          data-level="control"
          onClick={onReset}
          className="ui-button ui-focus-ring"
        >
          <RotateCcw className="size-3" aria-hidden />
          reset
        </button>
      </div>
      <div className="mt-1">
        {(section.fields ?? []).map((entry) => (
          <Field key={entry.id} label={entry.label} value={entry.value} title={entry.title} />
        ))}
      </div>
    </div>
  );
}

function NavigatorSections({
  navigator,
  selected,
  metaGraph,
  colors,
  graph,
  groupFilter,
  onGroupFilter,
  onSelectNode,
  onSelectEdge,
  focusMode,
  onToggleFocus,
  onReset,
}: {
  navigator: TopologyNavigatorModel;
  selected: TopologySelection | undefined;
  metaGraph: TopologyModel["metaGraph"];
  colors: Map<string, string>;
  graph: MapGraph;
  groupFilter: string | undefined;
  onGroupFilter: (group: string | undefined) => void;
  onSelectNode: (name: string) => void;
  onSelectEdge: (name: string) => void;
  focusMode: boolean;
  onToggleFocus: () => void;
  onReset: () => void;
}) {
  const selectedName = selected?.name ?? "";
  return (
    <>
      {navigator.sections.map((section) => {
        const annotation = section.annotations ? (
          <AnnotationPopover
            annotations={section.annotations.annotations}
            context={section.annotations.context}
            metaGraph={metaGraph}
            compact
          />
        ) : null;

        const sectionActions =
          section.id === "groups" && groupFilter ? (
            <button
              type="button"
              data-level="control"
              onClick={() => onGroupFilter(undefined)}
              className="ui-focus-ring ml-auto cursor-pointer px-1 text-[9px] text-faint transition-colors hover:text-accent"
            >
              clear
            </button>
          ) : annotation ? (
            <div className="ml-auto">{annotation}</div>
          ) : null;

        return (
          <Section
            key={section.id}
            title={section.title}
            question={section.question}
            count={section.count}
            actions={sectionActions}
          >
            {section.id === "selection" ? (
              <NavigatorSelection
                section={section}
                focusMode={focusMode}
                onToggleFocus={onToggleFocus}
                onReset={onReset}
              />
            ) : null}

            {section.id === "groups" ? (
              <>
                {section.rows.map((row) => {
                  const active = groupFilter === row.label;
                  return (
                    <Row
                      key={row.id}
                      as="button"
                      interactive
                      selected={active}
                      data-testid={`map-group-${row.label}`}
                      data-selected={active ? "true" : undefined}
                      aria-pressed={active}
                      onClick={() => onGroupFilter(active ? undefined : row.label)}
                      title={`${active ? "Clear" : "Filter to"} ${row.label}`}
                      className="w-full"
                    >
                      <span
                        className="size-1.5 shrink-0 rounded-full"
                        style={{ backgroundColor: colors.get(row.label) ?? theme.faint }}
                        aria-hidden
                      />
                      <span className="min-w-0 flex-1 truncate font-mono text-[10.5px]">
                        {row.label}
                      </span>
                      <span className="ui-row-meta">{row.meta}</span>
                    </Row>
                  );
                })}
              </>
            ) : null}

            {section.id === "properties" ? (
              <>
                {section.rows.length ? (
                  section.rows.map((row) => {
                    const open = row.actions?.find((action) => action.id === "open-property");
                    return (
                      <Row
                        key={row.id}
                        as="button"
                        interactive
                        data-testid={`map-property-${selectedName}-${row.label}`}
                        onClick={() => open?.run()}
                        title={row.title ?? open?.title}
                        className="group w-full items-start py-1"
                      >
                        <span className="min-w-0 flex-1">
                          <span className="flex items-baseline gap-2">
                            <span className="min-w-0 flex-1 truncate font-mono text-[10.5px] text-text group-hover:text-accent">
                              {row.label}
                            </span>
                            <span className="ui-row-meta">{row.meta}</span>
                          </span>
                          <span className="mt-0.5 flex flex-wrap items-center gap-1">
                            <PropertyBadges badges={row.badges ?? []} />
                          </span>
                        </span>
                        <ChevronRight className="mt-1 size-3 shrink-0 text-faint" aria-hidden />
                      </Row>
                    );
                  })
                ) : (
                  <p className="ui-hint px-2 py-1.5">{section.empty}</p>
                )}
              </>
            ) : null}

            {section.id === "neighbours" ? (
              <>
                {section.notice ? (
                  <p
                    data-testid="map-neighbor-notice"
                    className="ui-hint flex items-center gap-1 px-2 py-1"
                  >
                    <Info className="size-3 shrink-0 text-accent" aria-hidden />
                    {section.notice}
                  </p>
                ) : null}
                {section.rows.length ? (
                  section.rows.map((row) => {
                    const group = graph.byName.get(row.label)?.group;
                    const color = group ? colors.get(group) : undefined;
                    const edgeSuffix =
                      selected?.kind === "edge" && row.direction === "in"
                        ? "-in"
                        : "";
                    return (
                      <Row key={row.id}>
                        {row.direction === "out" ? (
                          <ArrowUpRight className="size-3 shrink-0 text-accent" aria-hidden />
                        ) : (
                          <ArrowDownLeft className="size-3 shrink-0 text-faint" aria-hidden />
                        )}
                        <span
                          className="size-1.5 shrink-0 rounded-full"
                          style={{ backgroundColor: color ?? theme.faint }}
                          aria-hidden
                        />
                        <button
                          type="button"
                          data-testid={`map-neighbor-${row.label}`}
                          onClick={() => onSelectNode(row.label)}
                          className="ui-focus-ring min-w-0 flex-1 cursor-pointer truncate text-left font-mono text-[10.5px] text-text hover:text-accent"
                        >
                          {row.label}
                        </button>
                        <button
                          type="button"
                          data-testid={`map-neighbor-edge-${row.edge}${edgeSuffix}`}
                          onClick={() => row.edge && onSelectEdge(row.edge)}
                          className="ui-row-meta ui-focus-ring max-w-[45%] cursor-pointer truncate hover:text-accent"
                          title={row.edge}
                        >
                          {row.edge}
                        </button>
                      </Row>
                    );
                  })
                ) : (
                  <p className="ui-hint px-2 py-1.5">{section.empty}</p>
                )}
              </>
            ) : null}
          </Section>
        );
      })}
    </>
  );
}

export interface TopologyViewProps {
  model: TopologyModel;
}

/**
 * The Orientation canvas binds to an injected `TopologyModel`.
 *
 * Layout, viewport, pan/zoom, hover and the local group filter are view state.
 * The graph, the selected subject and the Navigator sections are model data.
 */
export function TopologyView({ model }: TopologyViewProps) {
  const graph = useMemo(() => layout(model), [model.canvas.graphKey]);
  const bounds = useMemo(() => {
    const xs = graph.nodes.map((node) => node.x);
    const ys = graph.nodes.map((node) => node.y);
    const minX = Math.min(...xs) - 110;
    const minY = Math.min(...ys) - 90;
    const maxX = Math.max(...xs) + 110;
    const maxY = Math.max(...ys) + 90;
    return {
      minX,
      minY,
      width: maxX - minX,
      height: maxY - minY,
      centerX: (minX + maxX) / 2,
      centerY: (minY + maxY) / 2,
    };
  }, [graph.nodes]);
  const viewBox = `${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}`;

  const [selected, setSelected] = useState<TopologySelection | undefined>(
    () => model.canvas.selected,
  );
  const navigator = useMemo(
    () => model.navigatorFor(selected),
    [model, selected],
  );
  const [linkHover, setLinkHover] = useState<LinkHoverState | undefined>();
  const [groupFilter, setGroupFilter] = useState<string | undefined>();
  const [focusMode, setFocusMode] = useState(false);
  const [dragging, setDragging] = useState(false);

  const wrapperRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const sceneRef = useRef<SVGGElement>(null);
  const zoomLevelRef = useRef<HTMLSpanElement>(null);
  const viewportRef = useRef<Viewport>(IDENTITY_VIEW);
  const wheelPendingRef = useRef<{ anchor: { x: number; y: number }; factor: number } | undefined>(
    undefined,
  );
  const wheelFrameRef = useRef<number | null>(null);
  const panFrameRef = useRef<number | null>(null);
  const dragRef = useRef<DragState | undefined>(undefined);
  const suppressClickRef = useRef(false);

  const applyViewport = useCallback((next: Viewport) => {
    viewportRef.current = next;
    const scene = sceneRef.current;
    if (scene) {
      scene.setAttribute(
        "transform",
        `translate(${next.x} ${next.y}) scale(${next.k})`,
      );
    }
    const level = zoomLevelRef.current;
    if (level) {
      const percent = Math.round(next.k * 100);
      level.textContent = `${percent}%`;
      level.setAttribute("aria-label", `Zoom ${percent} percent`);
    }
  }, []);

  const cancelViewportFrames = useCallback(() => {
    if (wheelFrameRef.current !== null) {
      window.cancelAnimationFrame(wheelFrameRef.current);
      wheelFrameRef.current = null;
    }
    if (panFrameRef.current !== null) {
      window.cancelAnimationFrame(panFrameRef.current);
      panFrameRef.current = null;
    }
    wheelPendingRef.current = undefined;
  }, []);

  const flushWheel = useCallback(() => {
    wheelFrameRef.current = null;
    const pending = wheelPendingRef.current;
    wheelPendingRef.current = undefined;
    if (!pending) return;
    const current = viewportRef.current;
    applyViewport(zoomAt(current, pending.anchor, current.k * pending.factor));
  }, [applyViewport]);

  const flushPan = useCallback(() => {
    if (panFrameRef.current !== null) {
      window.cancelAnimationFrame(panFrameRef.current);
      panFrameRef.current = null;
    }
    const drag = dragRef.current;
    if (!drag?.moved || !drag.latestView) return;
    applyViewport({
      x: drag.startPan.x + (drag.latestView.x - drag.startView.x),
      y: drag.startPan.y + (drag.latestView.y - drag.startView.y),
      k: drag.startPan.k,
    });
  }, [applyViewport]);

  const fitView = useCallback(() => {
    cancelViewportFrames();
    applyViewport(IDENTITY_VIEW);
  }, [applyViewport, cancelViewportFrames]);

  const selectNode = useCallback(
    (name: string) => setSelected({ kind: "node", name }),
    [],
  );

  const selectLink = useCallback(
    (edgeName: string) => setSelected({ kind: "edge", name: edgeName }),
    [],
  );

  const handleNodeClick = useCallback(
    (name: string) => {
      if (suppressClickRef.current) return;
      selectNode(name);
    },
    [selectNode],
  );

  const handleLinkClick = useCallback(
    (edgeName: string) => {
      if (suppressClickRef.current) return;
      selectLink(edgeName);
    },
    [selectLink],
  );

  const handleLinkHover = useCallback(
    (link: MapLink | undefined, clientX?: number, clientY?: number) => {
      if (!link || clientX === undefined || clientY === undefined) {
        setLinkHover(undefined);
        return;
      }
      const wrapper = wrapperRef.current;
      if (!wrapper) return;
      const rect = wrapper.getBoundingClientRect();
      const x = clientX - rect.left;
      const y = clientY - rect.top;
      setLinkHover({
        link,
        pointer: {
          x,
          y,
          flipX: x > rect.width - 250,
          flipY: y > rect.height - 100,
        },
      });
    },
    [],
  );

  const toggleFocus = useCallback(() => {
    setFocusMode((value) => !value);
  }, []);

  const resetAll = useCallback(() => {
    cancelViewportFrames();
    applyViewport(IDENTITY_VIEW);
    dragRef.current = undefined;
    setSelected(undefined);
    setGroupFilter(undefined);
    setFocusMode(false);
    setLinkHover(undefined);
    setDragging(false);
  }, [applyViewport, cancelViewportFrames]);

  const zoomFromCentre = useCallback(
    (factor: number) => {
      flushWheel();
      const current = viewportRef.current;
      applyViewport(
        zoomAt(
          current,
          { x: bounds.centerX, y: bounds.centerY },
          current.k * factor,
        ),
      );
    },
    [applyViewport, bounds.centerX, bounds.centerY, flushWheel],
  );

  useEffect(() => {
    cancelViewportFrames();
    applyViewport(IDENTITY_VIEW);
    setSelected(model.canvas.selected);
    setGroupFilter(undefined);
    setFocusMode(false);
    setLinkHover(undefined);
    setDragging(false);
    dragRef.current = undefined;
  }, [applyViewport, cancelViewportFrames, model.canvas.graphKey]);

  useEffect(() => {
    return () => cancelViewportFrames();
  }, [cancelViewportFrames]);

  const colors = useMemo(() => {
    // Amber is the selection/interaction colour here, so the shared palette is
    // used without its amber binding lane.
    const tones = groupPalette.filter((_tone, position) => position !== 3);
    return new Map(
      model.canvas.groups.map((group, position) => [
        group.name,
        tones[position % tones.length],
      ]),
    );
  }, [model.canvas.groups]);

  const groupCounts: Array<[string, number]> = model.canvas.groups.map((group) => [
    group.name,
    group.count,
  ]);

  const focusedCount = useMemo(() => {
    if (!selected) return 0;
    const names = new Set<string>();
    if (selected.kind === "node") names.add(selected.name);
    for (const link of graph.links) {
      if (selected.kind === "node") {
        if (link.source === selected.name) names.add(link.target);
        if (link.target === selected.name) names.add(link.source);
      } else if (link.edgeName === selected.name) {
        names.add(link.source);
        names.add(link.target);
      }
    }
    return names.size;
  }, [graph.links, selected]);

  const onPointerDown = (event: React.PointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    flushWheel();
    suppressClickRef.current = false;
    const point = clientToView(event.currentTarget, event.clientX, event.clientY);
    if (!point) return;
    const target = event.target as Element | null;
    const nodeElement = target?.closest?.("[data-map-node]") as Element | null;
    const linkElement = target?.closest?.("[data-map-link]") as Element | null;
    const press = nodeElement?.getAttribute("data-map-node")
      ? { kind: "node" as const, name: nodeElement.getAttribute("data-map-node")! }
      : linkElement?.getAttribute("data-map-link")
        ? { kind: "link" as const, name: linkElement.getAttribute("data-map-link")! }
        : undefined;
    dragRef.current = {
      pointerId: event.pointerId,
      startClientX: event.clientX,
      startClientY: event.clientY,
      startView: point,
      startPan: viewportRef.current,
      moved: false,
      latestView: undefined,
      press,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  };

  const onPointerMove = (event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (
      !drag.moved &&
      Math.hypot(event.clientX - drag.startClientX, event.clientY - drag.startClientY) >
        DRAG_THRESHOLD
    ) {
      drag.moved = true;
    }
    if (!drag.moved) return;
    const point = clientToView(event.currentTarget, event.clientX, event.clientY);
    if (!point) return;
    drag.latestView = point;
    if (panFrameRef.current === null) {
      panFrameRef.current = window.requestAnimationFrame(flushPan);
    }
  };

  const onPointerUp = (event: React.PointerEvent<SVGSVGElement>) => {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    flushPan();
    if (drag.moved) {
      suppressClickRef.current = true;
    } else if (drag.press) {
      if (drag.press.kind === "node") selectNode(drag.press.name);
      else selectLink(drag.press.name);
    }
    dragRef.current = undefined;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const onPointerCancel = (event: React.PointerEvent<SVGSVGElement>) => {
    if (panFrameRef.current !== null) {
      window.cancelAnimationFrame(panFrameRef.current);
      panFrameRef.current = null;
    }
    dragRef.current = undefined;
    setDragging(false);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  useEffect(() => {
    const wrapper = wrapperRef.current;
    const svg = svgRef.current;
    if (!wrapper || !svg) return;
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const point = clientToView(svg, event.clientX, event.clientY);
      if (!point) return;
      const delta = event.deltaMode === 1 ? event.deltaY * 16 : event.deltaY;
      const factor = Math.exp(-delta * 0.0014);
      const pending = wheelPendingRef.current;
      wheelPendingRef.current = {
        anchor: point,
        factor: (pending?.factor ?? 1) * factor,
      };
      if (wheelFrameRef.current === null) {
        wheelFrameRef.current = window.requestAnimationFrame(flushWheel);
      }
    };
    wrapper.addEventListener("wheel", handleWheel, { passive: false });
    return () => wrapper.removeEventListener("wheel", handleWheel);
  }, [flushWheel]);

  return (
    <div
      data-testid="topology-map"
      data-level="panel"
      aria-label="Orientation"
      className="flex h-full min-h-0 w-full min-w-0 flex-1 flex-col overflow-hidden bg-abyss"
    >
      <PanelHeader
        title={model.title}
        icon={<Orbit className="size-3.5" />}
        meta={model.meta}
        actions={<span className="ui-hint">{model.hint}</span>}
      />
      <div className="flex min-h-0 flex-1 gap-[2px] bg-gutter">
        <div
          ref={wrapperRef}
          className="relative min-w-0 flex-1 overflow-hidden bg-abyss"
          aria-label="Topology map canvas"
        >
          <svg
            ref={svgRef}
            data-testid="topology-map-canvas"
            viewBox={viewBox}
            className={cx(
              "relative h-full w-full touch-none select-none",
              dragging
                ? "cursor-grabbing [&_[data-map-node]]:cursor-grabbing [&_[data-map-link]]:cursor-grabbing"
                : "cursor-grab [&_[data-map-node]]:cursor-pointer [&_[data-map-link]]:cursor-pointer",
            )}
            role="group"
            aria-label={`Topology map with ${graph.nodes.length} nodes and ${graph.links.length} links`}
            onPointerDown={onPointerDown}
            onPointerMove={onPointerMove}
            onPointerUp={onPointerUp}
            onPointerCancel={onPointerCancel}
            onDragStart={(event) => event.preventDefault()}
          >
            <defs>
              <pattern id="map-grid-minor" width="24" height="24" patternUnits="userSpaceOnUse">
                <path
                  d="M 24 0 L 0 0 0 24"
                  fill="none"
                  stroke={theme.lineSoft}
                  strokeWidth="0.55"
                  strokeOpacity="0.7"
                  vectorEffect="non-scaling-stroke"
                />
              </pattern>
              <pattern id="map-grid-major" width="120" height="120" patternUnits="userSpaceOnUse">
                <path
                  d="M 120 0 L 0 0 0 120"
                  fill="none"
                  stroke={theme.lineSoft}
                  strokeWidth="0.7"
                  strokeOpacity="0.8"
                  vectorEffect="non-scaling-stroke"
                />
              </pattern>
            </defs>

            <g ref={sceneRef}>
              <rect
                x={-4000}
                y={-4000}
                width={10000}
                height={10000}
                fill="url(#map-grid-minor)"
                pointerEvents="none"
              />
              <rect
                x={-4000}
                y={-4000}
                width={10000}
                height={10000}
                fill="url(#map-grid-major)"
                pointerEvents="none"
              />
              <MapScene
                graph={graph}
                colors={colors}
                selected={selected}
                groupFilter={groupFilter}
                focusMode={focusMode}
                onSelectNode={selectNode}
                onSelectEdge={selectLink}
                onNodeClick={handleNodeClick}
                onLinkClick={handleLinkClick}
                onLinkHover={handleLinkHover}
              />
            </g>
          </svg>

          {focusMode && selected ? (
            <div
              data-testid="map-focus-state"
              data-level="canvas-overlay"
              className="ui-chip ui-chip-active pointer-events-none absolute top-2 left-2 z-10 px-2 py-0.5"
            >
              focused · {focusedCount}
            </div>
          ) : null}

          <div
            data-level="canvas-overlay"
            className="pointer-events-none absolute bottom-2 left-2 z-20 flex flex-col items-start gap-1"
          >
            <span className="ui-hint px-0.5">drag pan · wheel zoom · click select</span>
            <div className="flex items-stretch border border-line-soft bg-panel">
              <button
                type="button"
                data-testid="map-zoom-out"
                onClick={() => zoomFromCentre(1 / 1.25)}
                className="ui-icon-button ui-focus-ring size-6 rounded-none border-r border-line"
                aria-label="Zoom out"
                title="Zoom out"
              >
                <Minus className="size-3" aria-hidden />
              </button>
              <ZoomReadout levelRef={zoomLevelRef} />
              <button
                type="button"
                data-testid="map-zoom-in"
                onClick={() => zoomFromCentre(1.25)}
                className="ui-icon-button ui-focus-ring size-6 rounded-none border-x border-line"
                aria-label="Zoom in"
                title="Zoom in"
              >
                <Plus className="size-3" aria-hidden />
              </button>
              <button
                type="button"
                data-testid="map-zoom-fit"
                onClick={fitView}
                className="ui-icon-button ui-focus-ring size-6 rounded-none border-l border-line"
                aria-label="Fit the whole graph in view"
                title="Fit the whole graph in view"
              >
                <Maximize2 className="size-3" aria-hidden />
              </button>
            </div>
          </div>

          <div
            data-testid="map-legend"
            data-level="canvas-overlay"
            className="pointer-events-none absolute right-2 bottom-2 z-10 hidden w-[188px] overflow-hidden border border-line-soft bg-panel sm:block"
          >
            <div className="flex items-center justify-between border-b border-line-soft px-2 py-0.5">
              <span className="ui-label text-faint">keys</span>
              <span className="font-mono text-[9px] text-faint tabular-nums">
                {graph.nodes.length} / {graph.links.length}
              </span>
            </div>
            <div className="space-y-0.5 px-2 py-1">
              {groupCounts.map(([group, count]) => (
                <div key={group} className="flex items-center gap-1.5">
                  <span
                    className="size-1.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colors.get(group) ?? theme.faint }}
                    aria-hidden
                  />
                  <span className="min-w-0 flex-1 truncate font-mono text-[9px] text-muted">
                    {group}
                  </span>
                  <span className="font-mono text-[9px] text-faint tabular-nums">{count}</span>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 border-t border-line-soft px-2 py-1 font-mono text-[9px]">
              <span className="inline-flex items-center gap-1 text-faint">
                <span
                  className="h-px w-4 shrink-0"
                  style={{ backgroundColor: theme.edge }}
                  aria-hidden
                />
                edge
              </span>
              <span className="inline-flex items-center gap-1 text-accent-strong">
                <span className="h-px w-4 shrink-0 bg-accent" aria-hidden />
                hover
              </span>
              <span className="inline-flex items-center gap-1" style={{ color: theme.selection }}>
                <span
                  className="h-px w-4 shrink-0"
                  style={{ backgroundColor: theme.selection }}
                  aria-hidden
                />
                selected
              </span>
            </div>
          </div>

          {linkHover ? (
            <div
              className="pointer-events-none absolute z-20 max-w-[250px] overflow-hidden border border-line-soft bg-panel"
              style={{
                left: linkHover.pointer.x,
                top: linkHover.pointer.y,
                transform: `translate(${
                  linkHover.pointer.flipX ? "calc(-100% - 12px)" : "12px"
                }, ${linkHover.pointer.flipY ? "calc(-100% - 12px)" : "12px"})`,
              }}
            >
              <p className="border-b border-line-soft px-2 py-1 font-mono text-[10px] break-words text-accent-strong">
                {linkHover.link.edgeName}
              </p>
              <p className="px-2 py-1 font-mono text-[9px] break-words text-faint">
                {linkHover.link.source} <span className="text-accent/70">→</span>{" "}
                {linkHover.link.target}
              </p>
            </div>
          ) : null}
        </div>

        <aside
          data-testid="map-panel"
          data-level="panel"
          className="ui-properties flex w-[340px] shrink-0 flex-col overflow-hidden xl:w-[372px]"
        >
          <PanelHeader title={navigator.title} meta={navigator.meta} />
          <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto">
            <NavigatorSections
              navigator={navigator}
              selected={selected}
              metaGraph={model.metaGraph}
              colors={colors}
              graph={graph}
              groupFilter={groupFilter}
              onGroupFilter={setGroupFilter}
              onSelectNode={selectNode}
              onSelectEdge={selectLink}
              focusMode={focusMode}
              onToggleFocus={toggleFocus}
              onReset={resetAll}
            />
          </div>
        </aside>
      </div>
    </div>
  );
}

export const TopologyMapView = TopologyView;
