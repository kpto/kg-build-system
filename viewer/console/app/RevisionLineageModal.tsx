"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";

import { Control, Label, Meta } from "@kbs/design";

import { ConceptPill, CONCEPTS, conceptFor } from "./concepts";
import styles from "./lineage.module.css";

type LineageEntity = {
  id: string;
  kind: string;
  title: string;
  created?: string;
  state?: string;
  fields?: { label: string; value: string }[];
  links?: { id: string; kind: string; role?: string }[];
};

type TimelineEvent = {
  id: string;
  type: string;
  revision_id?: string | null;
  prev?: string[];
  refs?: { kind: string; id: string }[];
};

type Layer = 0 | 1 | 2 | 3;

const GRAPH_KINDS = new Set(["finding", "proposal", "change_design", "revision"]);
const LAYER: Record<string, Layer> = {
  finding: 0,
  proposal: 1,
  change_design: 2,
  revision: 3,
};
const LAYER_LABEL = ["Findings", "Proposals", "Designs", "Revision"];

function stateOf(entity: LineageEntity): string {
  return (
    entity.state ??
    entity.fields?.find((field) => field.label.toLowerCase() === "state")?.value ??
    ""
  ).toLowerCase();
}

function isRejected(entity: LineageEntity): boolean {
  return ["rejected", "abandoned"].includes(stateOf(entity));
}

function eventEntity(event: TimelineEvent): { kind: string; id: string } | null {
  if (event.type.startsWith("design_")) {
    return { kind: "change_design", id: event.id.split(":state:")[0] };
  }
  if (event.type === "kg_edited" || event.type.startsWith("revision")) {
    const revision =
      event.revision_id || event.refs?.find((ref) => ref.kind === "revision")?.id;
    if (revision) return { kind: "revision", id: revision };
  }
  // An evaluation run carries the revision it measured but is not a revision
  // boundary; walking through it reaches the designs recorded before it.
  return null;
}

/**
 * The design entities that lead to a revision, read from the iteration event
 * chain. A revision event names the design state it follows; walking `prev`
 * until the previous revision collects every design recorded since then.
 */
function designAncestors(events: TimelineEvent[], revisionId: string): Set<string> {
  const byId = new Map(events.map((event) => [event.id, event]));
  const starts = events.filter((event) => {
    const entity = eventEntity(event);
    return entity?.kind === "revision" && entity.id === revisionId;
  });
  const designs = new Set<string>();
  const seen = new Set<string>();
  const walk = (event: TimelineEvent) => {
    for (const prevId of event.prev ?? []) {
      if (seen.has(prevId)) continue;
      seen.add(prevId);
      const previous = byId.get(prevId);
      if (!previous) continue;
      const entity = eventEntity(previous);
      if (entity?.kind === "revision") continue;
      if (entity?.kind === "change_design") designs.add(entity.id);
      walk(previous);
    }
  };
  for (const start of starts) walk(start);
  return designs;
}

function buildLineage(
  objects: LineageEntity[],
  events: TimelineEvent[],
  revisionId: string,
) {
  const byId = new Map(
    objects
      .filter((object) => GRAPH_KINDS.has(object.kind) && object.id !== revisionId)
      .map((object) => [object.id, object]),
  );
  const revision = objects.find((object) => object.id === revisionId);
  if (!revision) return null;
  byId.set(revision.id, revision);

  const ancestors = designAncestors(events, revisionId);
  const included = new Set<string>();
  const queue = [revisionId, ...ancestors];
  while (queue.length) {
    const id = queue.shift();
    if (!id || included.has(id) || !byId.has(id)) continue;
    included.add(id);
    const entity = byId.get(id);
    if (!entity) continue;
    const sourceLayer = LAYER[entity.kind];
    for (const link of entity.links ?? []) {
      if (!GRAPH_KINDS.has(link.kind)) continue;
      const target = byId.get(link.id);
      if (!target) continue;
      // The lineage reads down the layers: a finding does not introduce the
      // other designs that cite it.
      if (LAYER[target.kind] >= sourceLayer) continue;
      queue.push(link.id);
    }
  }

  for (const entity of byId.values()) {
    if (!isRejected(entity) || included.has(entity.id)) continue;
    if (!["proposal", "change_design"].includes(entity.kind)) continue;
    const rejectedQueue = [entity.id];
    while (rejectedQueue.length) {
      const id = rejectedQueue.shift();
      if (!id || included.has(id) || !byId.has(id)) continue;
      included.add(id);
      const current = byId.get(id);
      if (!current) continue;
      const currentLayer = LAYER[current.kind];
      for (const link of current.links ?? []) {
        if (!GRAPH_KINDS.has(link.kind)) continue;
        const target = byId.get(link.id);
        if (!target) continue;
        if (LAYER[target.kind] >= currentLayer) continue;
        rejectedQueue.push(link.id);
      }
    }
  }

  const edges: { from: string; to: string; considered: boolean }[] = [];
  const edgeKeys = new Set<string>();
  const addEdge = (from: string, to: string, considered = false) => {
    if (from === to) return;
    const source = byId.get(from);
    const target = byId.get(to);
    if (!source || !target) return;
    const sourceLayer = LAYER[source.kind];
    const targetLayer = LAYER[target.kind];
    if (sourceLayer === targetLayer) return;
    const [left, right] =
      sourceLayer < targetLayer ? [from, to] : [to, from];
    const key = `${left}->${right}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    edges.push({ from: left, to: right, considered });
  };

  for (const id of included) {
    const entity = byId.get(id);
    for (const link of entity?.links ?? []) {
      if (!included.has(link.id) || !GRAPH_KINDS.has(link.kind)) continue;
      addEdge(id, link.id);
    }
  }

  // The event chain is the provenance of a revision recorded without an
  // explicit produced_by field.
  for (const id of ancestors) {
    if (included.has(id)) addEdge(id, revisionId);
  }

  // A rejected branch is not provenance, but it was considered when the
  // revision was recorded. Carry the top of each rejected branch to the
  // revision with a dashed edge.
  for (const id of included) {
    const entity = byId.get(id);
    if (!entity || !isRejected(entity)) continue;
    const hasDesignChild = (entity.links ?? []).some(
      (link) => link.kind === "change_design" && included.has(link.id),
    );
    if (entity.kind === "proposal" && hasDesignChild) continue;
    addEdge(id, revisionId, true);
  }

  const nodes = [...included]
    .map((id) => byId.get(id))
    .filter((entity): entity is LineageEntity => Boolean(entity))
    .sort((left, right) => {
      const layer = LAYER[left.kind] - LAYER[right.kind];
      if (layer) return layer;
      return (
        String(left.created ?? "").localeCompare(String(right.created ?? "")) ||
        left.id.localeCompare(right.id)
      );
    });
  const perLayer = new Map<Layer, number>();
  const maxRows = Math.max(
    1,
    ...nodes.map((node) => {
      const index = perLayer.get(LAYER[node.kind]) ?? 0;
      perLayer.set(LAYER[node.kind], index + 1);
      return index + 1;
    }),
  );
  const layerCounts = [0, 1, 2, 3].map(
    (layer) => nodes.filter((node) => LAYER[node.kind] === layer).length,
  );
  const positioned = nodes.map((node) => {
    const layer = LAYER[node.kind];
    const index = nodes
      .filter((candidate) => LAYER[candidate.kind] === layer)
      .findIndex((candidate) => candidate.id === node.id);
    return { entity: node, layer, index };
  });
  return { revision, nodes: positioned, edges, maxRows, layerCounts };
}

export function RevisionLineageModal({
  revisionId,
  objects,
  events,
  onOpen,
  onClose,
}: {
  revisionId: string;
  objects: LineageEntity[];
  events: TimelineEvent[];
  onOpen: (kind: string, id: string) => void;
  onClose: () => void;
}) {
  const lineage = useMemo(
    () => buildLineage(objects, events, revisionId),
    [events, objects, revisionId],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  const [zoom, setZoom] = useState(1);
  const viewportRef = useRef<HTMLDivElement>(null);

  const layout = useMemo(() => {
    if (!lineage) return null;
    const cardWidth = 216;
    const findingCardHeight = 72;
    const proposalCardHeight = 96;
    const designCardHeight = 112;
    const revisionCardHeight = 96;
    const columnGap = 28;
    const rowGap = 10;
    const padding = 24;
    const labelHeight = 18;
    const bandGap = 18;

    const byLayer = (layer: Layer) =>
      lineage.nodes
        .filter((node) => node.layer === layer)
        .sort(
          (left, right) =>
            String(left.entity.created ?? "").localeCompare(
              String(right.entity.created ?? ""),
            ) || left.entity.id.localeCompare(right.entity.id),
        );

    const findings = byLayer(0);
    const proposals = byLayer(1);
    const designs = byLayer(2);
    const revision = byLayer(3)[0];

    const designIndex = new Map(
      designs.map((node, index) => [node.entity.id, index]),
    );
    const parentsOf = new Map<string, string[]>();
    for (const edge of lineage.edges) {
      const source = lineage.nodes.find((node) => node.entity.id === edge.from);
      const target = lineage.nodes.find((node) => node.entity.id === edge.to);
      if (source?.layer === 0 && target?.layer === 2) {
        const list = parentsOf.get(edge.from) ?? [];
        list.push(edge.to);
        parentsOf.set(edge.from, list);
      }
    }

    const columns: (typeof findings)[] = designs.map(() => []);
    const other: typeof findings = [];
    for (const finding of findings) {
      const parents = (parentsOf.get(finding.entity.id) ?? []).filter((id) =>
        designIndex.has(id),
      );
      if (!parents.length) {
        other.push(finding);
        continue;
      }
      let target = parents[0];
      for (const parent of parents) {
        const candidate = designIndex.get(parent);
        const current = designIndex.get(target);
        if (
          candidate !== undefined &&
          current !== undefined &&
          columns[candidate].length < columns[current].length
        ) {
          target = parent;
        }
      }
      columns[designIndex.get(target)!].push(finding);
    }

    const columnCount = designs.length + (other.length ? 1 : 0);
    const rowCount = Math.max(1, columnCount, proposals.length);
    const width = padding * 2 + rowCount * (cardWidth + columnGap) - columnGap;
    const contentWidth = columnCount
      ? columnCount * (cardWidth + columnGap) - columnGap
      : 0;
    const contentStart = padding + (width - padding * 2 - contentWidth) / 2;
    const findingRows = Math.max(
      0,
      ...columns.map((column) => column.length),
      other.length,
    );

    const positions = new Map<
      string,
      { x: number; y: number; width: number; height: number }
    >();
    const bands: { labelY: number; top: number; height: number; count: number }[] = [];
    let cursor = padding;

    const revisionHeight = revision ? revisionCardHeight : 0;
    bands[3] = {
      labelY: cursor,
      top: cursor - 6,
      height: labelHeight + revisionHeight + 10,
      count: revision ? 1 : 0,
    };
    if (revision) {
      positions.set(revision.entity.id, {
        x: padding + (width - padding * 2 - cardWidth) / 2,
        y: cursor + labelHeight,
        width: cardWidth,
        height: revisionCardHeight,
      });
    }
    cursor += labelHeight + revisionHeight + bandGap;

    const designHeight = designs.length ? designCardHeight : 0;
    bands[2] = {
      labelY: cursor,
      top: cursor - 6,
      height: labelHeight + designHeight + 10,
      count: designs.length,
    };
    designs.forEach((design, index) => {
      positions.set(design.entity.id, {
        x: contentStart + index * (cardWidth + columnGap),
        y: cursor + labelHeight,
        width: cardWidth,
        height: designCardHeight,
      });
    });
    cursor += labelHeight + designHeight + bandGap;

    const proposalHeight = proposals.length ? proposalCardHeight : 0;
    bands[1] = {
      labelY: cursor,
      top: cursor - 6,
      height: labelHeight + proposalHeight + 10,
      count: proposals.length,
    };
    const proposalWidth = proposals.length
      ? proposals.length * (cardWidth + columnGap) - columnGap
      : 0;
    const proposalStart = padding + (width - padding * 2 - proposalWidth) / 2;
    proposals.forEach((proposal, index) => {
      positions.set(proposal.entity.id, {
        x: proposalStart + index * (cardWidth + columnGap),
        y: cursor + labelHeight,
        width: cardWidth,
        height: proposalCardHeight,
      });
    });
    cursor += labelHeight + proposalHeight + bandGap;

    const findingHeight = findingRows
      ? findingRows * findingCardHeight + (findingRows - 1) * rowGap
      : 0;
    bands[0] = {
      labelY: cursor,
      top: cursor - 6,
      height: labelHeight + findingHeight + 10,
      count: findings.length,
    };
    columns.forEach((column, columnIndex) => {
      column.forEach((finding, row) => {
        positions.set(finding.entity.id, {
          x: contentStart + columnIndex * (cardWidth + columnGap),
          y: cursor + labelHeight + row * (findingCardHeight + rowGap),
          width: cardWidth,
          height: findingCardHeight,
        });
      });
    });
    other.forEach((finding, row) => {
      positions.set(finding.entity.id, {
        x: contentStart + designs.length * (cardWidth + columnGap),
        y: cursor + labelHeight + row * (findingCardHeight + rowGap),
        width: cardWidth,
        height: findingCardHeight,
      });
    });
    cursor += labelHeight + findingHeight + bandGap;

    return {
      cardWidth,
      padding,
      width,
      height: cursor - bandGap + padding,
      positions,
      bands,
      counts: [findings.length, proposals.length, designs.length, revision ? 1 : 0],
    };
  }, [lineage]);

  const rejectedCount = lineage
    ? lineage.nodes.filter((node) => isRejected(node.entity)).length
    : 0;

  const [hovered, setHovered] = useState<string | null>(null);

  const incident = useMemo(() => {
    if (!hovered || !lineage) return new Set<string>();
    return new Set(
      lineage.edges
        .filter((edge) => edge.from === hovered || edge.to === hovered)
        .map((edge) => `${edge.from}->${edge.to}`),
    );
  }, [hovered, lineage]);

  const edgeGeometry = useMemo(() => {
    if (!lineage || !layout) return [];
    const incoming = new Map<string, typeof lineage.edges>();
    for (const edge of lineage.edges) {
      const group = incoming.get(edge.to) ?? [];
      group.push(edge);
      incoming.set(edge.to, group);
    }
    const ends = new Map<string, { x: number; y: number }>();
    for (const [targetId, group] of incoming) {
      const target = layout.positions.get(targetId);
      if (!target) continue;
      group.sort((left, right) => {
        const leftX = layout.positions.get(left.from)?.x ?? 0;
        const rightX = layout.positions.get(right.from)?.x ?? 0;
        return leftX - rightX || left.from.localeCompare(right.from);
      });
      const span =
        group.length > 1
          ? Math.min(target.width * 0.72, (group.length - 1) * 14)
          : 0;
      const start = target.x + target.width / 2 - span / 2;
      group.forEach((edge, index) => {
        ends.set(`${edge.from}->${edge.to}`, {
          x:
            group.length > 1
              ? start + index * (span / (group.length - 1))
              : target.x + target.width / 2,
          y: target.y + target.height,
        });
      });
    }
    return lineage.edges.flatMap((edge) => {
      const source = layout.positions.get(edge.from);
      const target = layout.positions.get(edge.to);
      const end = ends.get(`${edge.from}->${edge.to}`);
      if (!source || !target || !end) return [];
      const sx = source.x + source.width / 2;
      const sy = source.y;
      const shelf = end.y + 12;
      const path =
        Math.abs(sx - end.x) < 0.5
          ? `M ${sx} ${sy} L ${sx} ${end.y}`
          : `M ${sx} ${sy} L ${sx} ${shelf} L ${end.x} ${shelf} L ${end.x} ${end.y}`;
      return [{ edge, path, head: { x: end.x, y: end.y, angle: -90 } }];
    });
  }, [layout, lineage]);

  const fit = useCallback(() => {
    const element = viewportRef.current;
    if (!element || !layout) return;
    const scale = Math.max(
      0.35,
      Math.min(
        1,
        (element.clientWidth - 24) / layout.width,
        (element.clientHeight - 24) / layout.height,
      ),
    );
    setZoom(Number.isFinite(scale) ? scale : 1);
  }, [layout]);

  useEffect(() => {
    fit();
  }, [fit]);

  return (
    <div
      className={styles.overlay}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className={styles.dialog} role="dialog" aria-modal="true" aria-label="Revision lineage">
        <header className={styles.header}>
          <div className={styles.identity}>
            <Label>Revision lineage</Label>
            <h2 className={styles.title}>{lineage?.revision.title || revisionId}</h2>
            <Meta>{revisionId}</Meta>
          </div>
          <Control type="button" onClick={onClose}>
            Close
          </Control>
        </header>
        <div className={styles.legend}>
          <span><i className={styles.solid} />provenance</span>
          <span><i className={styles.dashed} />considered / rejected</span>
          <Meta>{rejectedCount} rejected</Meta>
          <div className={styles.controls}>
            <Control
              type="button"
              aria-label="Zoom out"
              onClick={() => setZoom((value) => Math.max(0.35, value / 1.2))}
            >
              −
            </Control>
            <Meta>{Math.round(zoom * 100)}%</Meta>
            <Control
              type="button"
              aria-label="Zoom in"
              onClick={() => setZoom((value) => Math.min(1.8, value * 1.2))}
            >
              +
            </Control>
            <Control type="button" onClick={fit}>
              Fit
            </Control>
          </div>
        </div>
        {lineage && layout ? (
          <div className={styles.viewport} ref={viewportRef}>
            <div
              className={styles.scaled}
              style={{ width: layout.width * zoom, height: layout.height * zoom }}
            >
              <div
                className={styles.canvas}
                style={{
                  width: layout.width,
                  height: layout.height,
                  transform: `scale(${zoom})`,
                }}
              >
                <svg className={styles.edges} width={layout.width} height={layout.height} aria-hidden="true">
                  {edgeGeometry.map(({ edge, path, head }) => {
                    const key = `${edge.from}->${edge.to}`;
                    const active = incident.has(key);
                    const stroke = edge.considered
                      ? "var(--color-rejected)"
                      : active
                        ? "var(--color-selection-strong)"
                        : "var(--color-selection)";
                    return (
                      <g key={key} opacity={hovered && !active ? 0.12 : 1}>
                        <path
                          className={
                            edge.considered ? styles.edgeDashed : styles.edge
                          }
                          d={path}
                          stroke={stroke}
                          strokeWidth={active ? 1.6 : 1}
                        />
                        <polygon
                          points="-10,-5 0,0 -10,5"
                          transform={`translate(${head.x} ${head.y}) rotate(${head.angle})`}
                          fill={stroke}
                        />
                      </g>
                    );
                  })}
                </svg>
                {[0, 1, 2, 3].map((layer) =>
                  layout.counts[layer] ? (
                    <span
                      key={layer}
                      className={styles.layerLabel}
                      data-layer={layer}
                      style={{
                        left: layout.padding,
                        top: layout.bands[layer].labelY,
                      }}
                    >
                      {LAYER_LABEL[layer]} {layout.counts[layer]}
                    </span>
                  ) : null,
                )}
                {lineage.nodes.map((node) => {
                  const position = layout.positions.get(node.entity.id);
                  if (!position) return null;
                  const rejected = isRejected(node.entity);
                  const concept = conceptFor(node.entity.kind);
                  const state = stateOf(node.entity);
                  const color = concept ? CONCEPTS[concept].color : undefined;
                  const dim = hovered !== null && hovered !== node.entity.id;
                  return (
                    <button
                      key={node.entity.id}
                      type="button"
                      className={styles.nodeButton}
                      style={{
                        left: position.x,
                        top: position.y,
                        width: position.width,
                        height: position.height,
                        opacity: dim ? 0.28 : 1,
                      }}
                      aria-label={`Open ${node.entity.kind.replaceAll("_", " ")} ${node.entity.id}`}
                      onClick={() => onOpen(node.entity.kind, node.entity.id)}
                      onMouseEnter={() => setHovered(node.entity.id)}
                      onMouseLeave={() => setHovered(null)}
                      onFocus={() => setHovered(node.entity.id)}
                      onBlur={() => setHovered(null)}
                    >
                      <div
                        className={styles.node}
                        data-kind={node.entity.kind}
                        data-rejected={rejected ? "true" : undefined}
                        style={
                          color
                            ? ({ "--node-color": color } as CSSProperties)
                            : undefined
                        }
                      >
                        <div className={styles.nodeMeta}>
                          {concept ? (
                            <ConceptPill
                              concept={concept}
                              label={
                                node.entity.kind === "finding"
                                  ? node.entity.id
                                  : undefined
                              }
                              size="md"
                              className={styles.nodePill}
                            />
                          ) : (
                            <span className={styles.nodeKind}>
                              {node.entity.kind.replaceAll("_", " ")}
                            </span>
                          )}
                          {state ? (
                            <span className={styles.nodeTag}>{state}</span>
                          ) : null}
                        </div>
                        <span className={styles.nodeText}>
                          {node.entity.title || node.entity.id}
                        </span>
                        {node.entity.kind === "finding" ? null : (
                          <span className={styles.nodeId}>{node.entity.id}</span>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.missing}>This revision is not in the catalog.</div>
        )}
      </div>
    </div>
  );
}
