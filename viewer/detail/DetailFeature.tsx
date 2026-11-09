"use client";

/**
 * Detail activity: one design subject read in full.
 *
 * The sidebar selects a design subject; the editor presents its meaning,
 * properties and, for a property, its provenance; the bottom panel exposes the
 * workflow trace and evidence. Provenance is a section of this view,
 * not a separate activity.
 */

import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  BadgeCheck,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Database,
  GitBranch,
  Layers,
  Network,
  Search,
  Waypoints,
} from "lucide-react";

import type {
  ActivityId,
  FeatureProps,
  WorkbenchSelection,
} from "@/workbench/types";
import type {
  LineageLane,
  SemanticSubjectKind,
} from "@/lib/types";
import { LINEAGE_LANES } from "@/lib/types";
import { logicalTypeName } from "@/lib/expressions";
import { resolveAssetName } from "@/lib/indexes";
import { laneColor } from "@/shared/ui/theme";
import {
  branchLaneNodes,
  buildProof,
  collectProofSemantics,
  defaultProofSubject,
  proofSubjectForLevel,
  resolveProofSubject,
  traceArtifactLabel,
  type ProofBranch,
  type ProofLevel,
  type ProofModel,
  type ProofNode,
  type ProofPropertySummary,
  type ProofSemantics,
  type ProofSubject,
  type ProofTrace,
  type ProofTypeChain,
} from "@/proof/model";
import { DesignMeaning, GraphMeaning } from "@/shared/design/DesignMeaning";
import {
  attachedMeaning,
  componentMeaning,
  graphMeaning,
  propertyMeaning,
  type DesignMeaningValue,
} from "@/shared/design/meaning";
import styles from "./detail.module.css";

// ---------------------------------------------------------------------------
// Selection plumbing
// ---------------------------------------------------------------------------

function toWorkbenchSelection(
  subject: ProofSubject,
  activity: WorkbenchSelection["activity"],
): WorkbenchSelection {
  const base: WorkbenchSelection = {
    activity,
    name:
      subject.level === "property"
        ? `${subject.component}.${subject.property ?? ""}`
        : subject.component,
    component: subject.component,
    level: subject.level,
  };
  switch (subject.level) {
    case "property":
      return {
        ...base,
        kind: "property",
        property: subject.property,
      };
    case "node":
      return { ...base, kind: "node" };
    case "edge":
      return { ...base, kind: "edge" };
    case "asset":
      return { ...base, kind: "asset" };
    case "abstract":
      return { ...base, kind: "node" };
  }
}

function useProofModel(props: FeatureProps): ProofModel {
  const selection = props.state.functions[props.activity].selection;
  return useMemo(
    () => buildProof(props.state.index, selection),
    [props.state.index, selection],
  );
}

function useCurrentSubject(props: FeatureProps): ProofSubject {
  const selection = props.state.functions[props.activity].selection;
  return useMemo(
    () => resolveProofSubject(props.state.index, selection),
    [props.state.index, selection],
  );
}

const LEVELS: Array<{ id: ProofLevel; label: string }> = [
  { id: "property", label: "Property" },
  { id: "node", label: "Node" },
  { id: "edge", label: "Edge" },
  { id: "abstract", label: "Abstract" },
  { id: "asset", label: "Asset" },
];

function levelTitle(model: ProofModel): string {
  switch (model.level) {
    case "property":
      return `${model.subject.component}.${model.subject.property ?? ""}`;
    case "node":
      return `Node · ${model.subject.component}`;
    case "edge":
      return `Edge · ${model.subject.component}`;
    case "abstract":
      return `Abstract · ${model.abstract?.name ?? model.subject.component}`;
    case "asset":
      return `Asset · ${model.asset?.name ?? model.subject.component}`;
  }
}

function levelSubtitle(model: ProofModel): string {
  switch (model.level) {
    case "property": {
      const branchCount = model.branches.length;
      const type = model.typeChain?.steps.at(0)?.typeName ?? "unknown";
      return `${branchCount} ${branchCount === 1 ? "branch" : "branches"} · ${type}`;
    }
    case "node":
    case "edge":
      return `${model.properties.length} ${model.properties.length === 1 ? "property" : "properties"} · ${model.component?.labels.join(", ") || "no labels"}`;
    case "abstract":
      return `${model.abstract?.descendants.length ?? 0} concrete descendants`;
    case "asset": {
      const relations = model.asset?.relations.length ?? 0;
      const projections = model.asset?.projections.length ?? 0;
      return `${relations} tables · ${projections} projections · ${model.asset?.fields.length ?? 0} fields`;
    }
  }
}

// ---------------------------------------------------------------------------
// Small shared pieces
// ---------------------------------------------------------------------------

function Badge({
  children,
  tone,
}: {
  children: ReactNode;
  tone?: "lane" | "muted" | "warn" | "ok";
}) {
  return (
    <span className={styles.badge} data-tone={tone ?? "muted"}>
      {children}
    </span>
  );
}

function Panel({
  title,
  meta,
  children,
  className,
}: {
  title: string;
  meta?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`${styles.panel} ${className ?? ""}`}>
      <header className={styles.panelHead}>
        <h2>{title}</h2>
        {meta ? <span className={styles.panelMeta}>{meta}</span> : null}
      </header>
      <div className={styles.panelBody}>{children}</div>
    </section>
  );
}

function EmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}

function attachmentLabel(kind: SemanticSubjectKind): string {
  switch (kind) {
    case "graph":
      return "graph declaration";
    case "binding":
      return "binding";
    case "field":
      return "source field";
    default:
      return kind;
  }
}

function SemanticCards({ attachments }: { attachments: ProofSemantics[] }) {
  if (!attachments.length) {
    return <EmptyState>No attached semantics on this subject.</EmptyState>;
  }
  return (
    <div className={styles.semanticGrid}>
      {attachments.map((attachment) => (
        <article key={attachment.key} className={styles.semanticCard}>
          <header className={styles.semanticHead}>
            <span className={styles.semanticKind}>
              {attachmentLabel(attachment.kind)}
            </span>
            <span className={styles.semanticName}>
              {attachment.ownerName
                ? `${attachment.ownerName}.${attachment.name}`
                : attachment.name}
            </span>
            <Badge tone="muted">attached</Badge>
          </header>
          {attachment.purpose ? (
            <div className={styles.purpose}>
              <p className={styles.purposeLabel}>Purpose</p>
              <p className={styles.purposeText}>{attachment.purpose.text}</p>
              <FrameList frames={attachment.purpose.frames ?? []} />
            </div>
          ) : null}
          {attachment.claims.length ? (
            <ul className={styles.claimList}>
              {attachment.claims.map((claim, index) => (
                <li key={`${attachment.key}:claim:${index}`}>{claim.text}</li>
              ))}
            </ul>
          ) : null}
          <FrameList frames={attachment.frames} />
        </article>
      ))}
    </div>
  );
}

function FrameList({
  frames,
}: {
  frames: Array<{ text: string; limitations?: Array<{ text: string }> }>;
}) {
  if (!frames.length) return null;
  return (
    <ul className={styles.frameList}>
      {frames.map((frame, index) => (
        <li key={`${frame.text}:${index}`}>
          <span className={styles.frameText}>{frame.text}</span>
          {frame.limitations?.length ? (
            <ul className={styles.limitList}>
              {frame.limitations.map((limitation, limitIndex) => (
                <li key={`${limitation.text}:${limitIndex}`}>
                  {limitation.text}
                </li>
              ))}
            </ul>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function TypeChainView({ chain }: { chain: ProofTypeChain }) {
  return (
    <Panel
      title="Type & presence"
      meta={
        <span className={styles.chainMeta}>
          {chain.mismatch ? (
            <Badge tone="warn">type mismatch</Badge>
          ) : (
            <Badge tone="ok">types agree</Badge>
          )}
          {chain.narrowed ? (
            <Badge tone="warn">declared present · source nullable</Badge>
          ) : null}
        </span>
      }
    >
      <div className={styles.chain}>
        {chain.steps.map((step, index) => (
          <div key={step.id} className={styles.chainItem}>
            <div
              className={styles.chainStep}
              data-stage={step.stage}
              data-presence={step.presence}
              data-mismatch={step.mismatch ? "true" : undefined}
            >
              <span className={styles.chainStage}>{step.stage}</span>
              <span className={styles.chainType}>{step.typeName ?? "—"}</span>
              <span className={styles.chainLabel}>{step.label}</span>
              {step.detail ? (
                <span className={styles.chainDetail}>{step.detail}</span>
              ) : null}
              <span className={styles.chainPresence}>{step.presence}</span>
            </div>
            {index < chain.steps.length - 1 ? (
              <ArrowRight aria-hidden className={styles.chainArrow} />
            ) : null}
          </div>
        ))}
      </div>
    </Panel>
  );
}

function TypeChainSummary({ chain }: { chain?: ProofTypeChain }) {
  if (!chain) return <Badge tone="muted">no type chain</Badge>;
  return (
    <>
      <span className={styles.summaryType}>
        {chain.steps.at(0)?.typeName ?? "unknown"}
      </span>
      {chain.mismatch ? <Badge tone="warn">type mismatch</Badge> : null}
      {chain.narrowed ? <Badge tone="warn">presence narrowing</Badge> : null}
    </>
  );
}

// ---------------------------------------------------------------------------
// Sidebar
// ---------------------------------------------------------------------------

function matches(query: string, ...values: Array<string | undefined>): boolean {
  if (!query) return true;
  return values.some((value) => value?.toLowerCase().includes(query));
}

function SideSection({
  id,
  title,
  count,
  open,
  onToggle,
  children,
}: {
  id: string;
  title: string;
  count: number;
  open: boolean;
  onToggle(id: string): void;
  children: ReactNode;
}) {
  return (
    <section className={styles.sideSection}>
      <button
        type="button"
        className={styles.sideSectionHead}
        aria-expanded={open}
        onClick={() => onToggle(id)}
      >
        {open ? (
          <ChevronDown aria-hidden className={styles.sideChevron} />
        ) : (
          <ChevronRight aria-hidden className={styles.sideChevron} />
        )}
        <span>{title}</span>
        <span className={styles.sideCount}>{count}</span>
      </button>
      {open ? <div className={styles.sideSectionBody}>{children}</div> : null}
    </section>
  );
}

interface SidebarRowProps {
  label: string;
  meta?: ReactNode;
  active?: boolean;
  abstract?: boolean;
  onSelect(): void;
}

function SidebarRow({ label, meta, active, abstract, onSelect }: SidebarRowProps) {
  return (
    <button
      type="button"
      className={styles.sideRow}
      data-active={active ? "true" : undefined}
      onClick={onSelect}
      title={label}
    >
      <span className={styles.sideRowLabel}>{label}</span>
      {abstract ? <span className={styles.sideAbstract}>abstract</span> : null}
      {meta ? <span className={styles.sideRowMeta}>{meta}</span> : null}
    </button>
  );
}

export function DetailSidebar(props: FeatureProps) {
  const { index } = props.state;
  const subject = useCurrentSubject(props);
  const model = useProofModel(props);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Set<string>>(
    () => new Set(["assets", "nodes", "abstract", "edges"]),
  );
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const normalized = query.trim().toLowerCase();

  const select = (next: ProofSubject) => {
    props.actions.setSelection(props.activity, toWorkbenchSelection(next, props.activity));
  };
  const toggle = (id: string) => {
    setOpen((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };
  const toggleNode = (name: string) => {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const assets = index.assets.filter((asset) => matches(normalized, asset.name));
  const relations = index.relations.filter((relation) =>
    matches(normalized, relation.name),
  );
  const projections = index.projections.filter((projection) =>
    matches(normalized, projection.name),
  );
  const nodes = index.topologyNodes.filter((node) =>
    matches(normalized, node.name) ||
    (node.properties ?? []).some((property) => matches(normalized, property.name)),
  );
  const edges = index.topologyEdges.filter((edge) =>
    matches(normalized, edge.name) ||
    (edge.properties ?? []).some((property) => matches(normalized, property.name)),
  );
  const concreteNodes = nodes.filter((node) => !node.abstract);
  const abstractNodes = nodes.filter((node) => node.abstract);

  const isActive = (
    level: ProofLevel,
    kind: string,
    component: string,
    property?: string,
  ): boolean =>
    subject.level === level &&
    subject.kind === kind &&
    subject.component === component &&
    (property === undefined || subject.property === property);

  const renderNode = (node: (typeof nodes)[number]) => {
    const nodeOpen = normalized ? true : expanded.has(`node:${node.name}`);
    const properties = (node.properties ?? []).filter((property) =>
      matches(normalized, property.name, node.name),
    );
    const nodeLevel: ProofLevel = node.abstract ? "abstract" : "node";
    const nodeKind: ProofSubject["kind"] = node.abstract ? "abstract" : "node";
    return (
      <div key={`node:${node.name}`} className={styles.treeBlock}>
        <div
          className={styles.treeRow}
          data-active={
            isActive(nodeLevel, nodeKind, node.name) ? "true" : undefined
          }
        >
          <button
            type="button"
            className={styles.treeToggle}
            aria-label={`${nodeOpen ? "Collapse" : "Expand"} ${node.name}`}
            aria-expanded={nodeOpen}
            onClick={() => toggleNode(node.name)}
          >
            {nodeOpen ? (
              <ChevronDown aria-hidden className={styles.sideChevron} />
            ) : (
              <ChevronRight aria-hidden className={styles.sideChevron} />
            )}
          </button>
          <button
            type="button"
            className={styles.treeLabel}
            onClick={() =>
              select({
                level: nodeLevel,
                kind: nodeKind,
                component: node.name,
              })
            }
            title={node.name}
          >
            <span>{node.name}</span>
            <span className={styles.treeMeta}>
              {node.properties?.length ?? 0}
            </span>
          </button>
        </div>
        {nodeOpen && properties.length ? (
          <div className={styles.treeChildren}>
            {properties.map((property) => (
              <button
                key={`${node.name}.${property.name}`}
                type="button"
                className={styles.propertyRow}
                data-active={
                  isActive("property", "node", node.name, property.name)
                    ? "true"
                    : undefined
                }
                onClick={() =>
                  select({
                    level: "property",
                    kind: "node",
                    component: node.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
              >
                <CircleDot aria-hidden className={styles.propertyDot} />
                <span>{property.name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  const renderEdge = (edge: (typeof edges)[number]) => {
    const edgeOpen = normalized ? true : expanded.has(`edge:${edge.name}`);
    const properties = (edge.properties ?? []).filter((property) =>
      matches(normalized, property.name, edge.name),
    );
    return (
      <div key={`edge:${edge.name}`} className={styles.treeBlock}>
        <div
          className={styles.treeRow}
          data-active={
            isActive("edge", "edge", edge.name) ? "true" : undefined
          }
        >
          <button
            type="button"
            className={styles.treeToggle}
            aria-label={`${edgeOpen ? "Collapse" : "Expand"} ${edge.name}`}
            aria-expanded={edgeOpen}
            onClick={() => toggleNode(`edge:${edge.name}`)}
          >
            {edgeOpen ? (
              <ChevronDown aria-hidden className={styles.sideChevron} />
            ) : (
              <ChevronRight aria-hidden className={styles.sideChevron} />
            )}
          </button>
          <button
            type="button"
            className={styles.treeLabel}
            onClick={() =>
              select({
                level: "edge",
                kind: "edge",
                component: edge.name,
              })
            }
            title={edge.name}
          >
            <span>{edge.name}</span>
            <span className={styles.treeMeta}>
              {edge.properties?.length ?? 0}
            </span>
          </button>
        </div>
        {edgeOpen && properties.length ? (
          <div className={styles.treeChildren}>
            {properties.map((property) => (
              <button
                key={`${edge.name}.${property.name}`}
                type="button"
                className={styles.propertyRow}
                data-active={
                  isActive("property", "edge", edge.name, property.name)
                    ? "true"
                    : undefined
                }
                onClick={() =>
                  select({
                    level: "property",
                    kind: "edge",
                    component: edge.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
              >
                <CircleDot aria-hidden className={styles.propertyDot} />
                <span>{property.name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className={styles.sidebar} data-testid="detail-sidebar">
      <header className="flex items-baseline justify-between border-b border-line-soft px-2.5 py-1.5">
        <p className="text-[9px] font-semibold tracking-[0.1em] text-text uppercase">
          Browse
        </p>
        <span className="font-mono text-[9px] text-faint tabular-nums">
          {index.stats.topologyNodes} nodes · {index.stats.topologyEdges} edges
        </span>
      </header>
      <div className={styles.search}>
        <Search aria-hidden className={styles.searchIcon} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter assets, nodes, properties"
          aria-label="Filter the design tree"
          spellCheck={false}
        />
      </div>
      <div className={`${styles.sideScroll} thin-scrollbar`}>
      <section className={styles.graphMeaning} aria-label="Graph meaning">
        <p className={styles.sideSectionTitle}>Graph purpose</p>
        <GraphMeaning
          claims={graphMeaning(index).claims}
          frames={graphMeaning(index).frames}
          purpose={graphMeaning(index).purpose}
        />
      </section>
        <SideSection
          id="assets"
          title="Assets"
          count={assets.length}
          open={open.has("assets")}
          onToggle={toggle}
        >
          {assets.map((asset) => (
            <SidebarRow
              key={asset.name}
              label={asset.name}
              meta={index.assetProfilesByName.get(asset.name)?.subject}
              active={isActive("asset", "asset", asset.name)}
              onSelect={() =>
                select({ level: "asset", kind: "asset", component: asset.name })
              }
            />
          ))}
        </SideSection>

        <SideSection
          id="relations"
          title="Relations"
          count={relations.length}
          open={open.has("relations")}
          onToggle={toggle}
        >
          {relations.map((relation) => (
            <SidebarRow
              key={relation.name}
              label={relation.name}
              meta={relation.columns?.length ?? 0}
              onSelect={() => {
                const assetName = resolveAssetName(index, relation.name);
                if (assetName) {
                  select({
                    level: "asset",
                    kind: "asset",
                    component: assetName,
                  });
                }
              }}
            />
          ))}
        </SideSection>

        <SideSection
          id="projections"
          title="Projections"
          count={projections.length}
          open={open.has("projections")}
          onToggle={toggle}
        >
          {projections.map((projection) => (
            <SidebarRow
              key={projection.name}
              label={projection.name}
              meta={projection.columns?.length ?? 0}
              onSelect={() => {
                const assetName = resolveAssetName(index, projection.name);
                if (assetName) {
                  select({
                    level: "asset",
                    kind: "asset",
                    component: assetName,
                  });
                }
              }}
            />
          ))}
        </SideSection>

        <SideSection
          id="nodes"
          title="Nodes"
          count={concreteNodes.length}
          open={open.has("nodes")}
          onToggle={toggle}
        >
          {concreteNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="abstract"
          title="Abstract"
          count={abstractNodes.length}
          open={open.has("abstract")}
          onToggle={toggle}
        >
          {abstractNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="edges"
          title="Edges"
          count={edges.length}
          open={open.has("edges")}
          onToggle={toggle}
        >
          {edges.map(renderEdge)}
        </SideSection>
      </div>
      <footer className={styles.sideFooter}>
        <span className={styles.sideFooterLabel}>Selection</span>
        <span className={styles.sideFooterValue}>{levelTitle(model)}</span>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor header
// ---------------------------------------------------------------------------

function LevelSelector({
  level,
  onChange,
}: {
  level: ProofLevel;
  onChange(level: ProofLevel): void;
}) {
  return (
    <div className={styles.levelSelector} role="tablist" aria-label="Design level">
      {LEVELS.map((entry) => (
        <button
          key={entry.id}
          type="button"
          role="tab"
          aria-selected={entry.id === level}
          className={styles.levelButton}
          data-active={entry.id === level ? "true" : undefined}
          onClick={() => onChange(entry.id)}
        >
          {entry.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Canvas
// ---------------------------------------------------------------------------

const LANE_WIDTH = 202;
const NODE_WIDTH = 176;
const NODE_HEIGHT = 64;
const ROW_GAP = 14;
const HEADER_HEIGHT = 28;
const PAD = 12;

interface NodePosition {
  x: number;
  y: number;
}

function LaneCanvas({ branch }: { branch: ProofBranch }) {
  const laneNodes = branchLaneNodes(branch);
  const rows = Math.max(
    1,
    ...LINEAGE_LANES.map((lane) => laneNodes.get(lane.id)?.length ?? 0),
  );
  const width = PAD * 2 + LANE_WIDTH * LINEAGE_LANES.length;
  const height = HEADER_HEIGHT + PAD * 2 + rows * (NODE_HEIGHT + ROW_GAP);
  const positions = new Map<string, NodePosition>();

  for (const [laneIndex, lane] of LINEAGE_LANES.entries()) {
    const nodes = laneNodes.get(lane.id) ?? [];
    for (const [rowIndex, node] of nodes.entries()) {
      positions.set(node.id, {
        x: PAD + laneIndex * LANE_WIDTH + (LANE_WIDTH - NODE_WIDTH) / 2,
        y: HEADER_HEIGHT + PAD + rowIndex * (NODE_HEIGHT + ROW_GAP),
      });
    }
  }

  const nodeById = new Map(branch.nodes.map((node) => [node.id, node]));

  return (
    <div className={styles.canvasShell}>
      <div className={`${styles.canvasScroll} thin-scrollbar`}>
        <div className={styles.canvas} style={{ width, height }}>
          {LINEAGE_LANES.map((lane, laneIndex) => (
            <div
              key={lane.id}
              className={styles.laneHeader}
              style={{
                left: PAD + laneIndex * LANE_WIDTH,
                width: NODE_WIDTH,
                top: 0,
              }}
            >
              <span>{lane.label}</span>
              <span>{laneNodes.get(lane.id)?.length ?? 0}</span>
            </div>
          ))}
          <svg
            className={styles.wires}
            width={width}
            height={height}
            aria-hidden
          >
            <defs>
              <marker
                id="proof-arrow"
                viewBox="0 0 8 8"
                refX="7"
                refY="4"
                markerWidth="7"
                markerHeight="7"
                orient="auto"
              >
                <path d="M0,0 L8,4 L0,8 z" fill="var(--color-edge)" />
              </marker>
            </defs>
            {branch.edges.map((edge) => {
              const source = positions.get(edge.source);
              const target = positions.get(edge.target);
              if (!source || !target) return null;
              const x1 = source.x + NODE_WIDTH;
              const y1 = source.y + NODE_HEIGHT / 2;
              const x2 = target.x;
              const y2 = target.y + NODE_HEIGHT / 2;
              const bend = Math.max(34, Math.abs(x2 - x1) * 0.45);
              const path =
                x2 >= x1
                  ? `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`
                  : `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
              return (
                <path
                  key={edge.id}
                  d={path}
                  className={styles.wire}
                  markerEnd="url(#proof-arrow)"
                >
                  {edge.label ? <title>{edge.label}</title> : null}
                </path>
              );
            })}
          </svg>
          {branch.nodes.map((node) => {
            const position = positions.get(node.id);
            if (!position) return null;
            return (
              <LaneNode
                key={node.id}
                node={node}
                position={position}
                selected={node.kind === "property"}
              />
            );
          })}
        </div>
      </div>
      <div className={styles.canvasLegend}>
        <span>
          <Waypoints aria-hidden className={styles.legendIcon} />
          {branch.edges.length} edges · {branch.nodes.length} nodes
        </span>
        <span className={styles.legendHint}>
          {nodeById.size} semantic and workflow nodes in this branch
        </span>
      </div>
    </div>
  );
}

function LaneNode({
  node,
  position,
  selected,
}: {
  node: ProofNode;
  position: NodePosition;
  selected: boolean;
}) {
  const style = {
    left: position.x,
    top: position.y,
    width: NODE_WIDTH,
    height: NODE_HEIGHT,
    "--lane-color": laneColor[node.lane],
  } as CSSProperties;
  return (
    <div
      className={styles.node}
      style={style}
      data-kind={node.kind}
      data-selected={selected ? "true" : undefined}
      title={`${node.label}${node.metadata.description ? ` — ${node.metadata.description}` : ""}`}
    >
      <span className={styles.nodeStripe} aria-hidden />
      <div className={styles.nodeHead}>
        <span className={styles.nodeLane}>{node.lane}</span>
        <span className={styles.nodeKind}>{node.kind}</span>
        {node.semantics.length ? (
          <span
            className={styles.nodeEvidence}
            title={`${node.semantics.length} attached semantics`}
          >
            {node.semantics.length}
          </span>
        ) : null}
      </div>
      <p className={styles.nodeLabel}>{node.label}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Property level
// ---------------------------------------------------------------------------

function BranchBar({
  branches,
  active,
  onChange,
}: {
  branches: ProofBranch[];
  active: number;
  onChange(index: number): void;
}) {
  return (
    <div className={styles.branchBar}>
      <span className={styles.toolLabel}>Branch</span>
      <div className={styles.branchPills}>
        {branches.map((branch, index) => (
          <button
            key={branch.key}
            type="button"
            className={styles.branchPill}
            data-active={index === active ? "true" : undefined}
            onClick={() => onChange(index)}
            title={branch.label}
          >
            <span className={styles.branchIndex}>
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className={styles.branchLabel}>{branch.label}</span>
          </button>
        ))}
      </div>
      <span className={styles.branchCount}>
        {branches.length} {branches.length === 1 ? "source" : "sources"}
      </span>
    </div>
  );
}

function ConnectionLedger({ branch }: { branch: ProofBranch }) {
  const labels = new Map(branch.nodes.map((node) => [node.id, node.label]));
  return (
    <Panel
      title="Connections"
      meta={`${branch.edges.length} edges`}
      className={styles.connectionPanel}
    >
      {branch.edges.length ? (
        <div className={styles.edgeList}>
          {branch.edges.map((edge) => (
            <div key={edge.id} className={styles.edgeRow}>
              <span className={styles.edgeEndpoint}>
                {labels.get(edge.source) ?? edge.source}
              </span>
              <ArrowRight aria-hidden className={styles.edgeArrow} />
              <span className={styles.edgeEndpoint}>
                {labels.get(edge.target) ?? edge.target}
              </span>
              {edge.label ? (
                <span className={styles.edgeLabel}>{edge.label}</span>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState>No edges in this branch.</EmptyState>
      )}
    </Panel>
  );
}

function PropertyProofView({ model }: { model: ProofModel }) {
  const [activeBranch, setActiveBranch] = useState(0);
  useEffect(() => {
    setActiveBranch(0);
  }, [model.property?.component, model.property?.property]);

  const branch = model.branches[activeBranch] ?? model.branches[0];
  const attachments = collectProofSemantics(model);

  if (!branch) {
    return (
      <div className={styles.emptyWrap}>
        <BadgeCheck aria-hidden className={styles.emptyIcon} />
        <h2>No binding for this property</h2>
        <p>
          The topology property is declared, but no blueprint binding resolves
          it to a source.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.levelBody}>
      <div className={styles.workToolbar}>
        <BranchBar
          branches={model.branches}
          active={activeBranch}
          onChange={setActiveBranch}
        />
        <div className={styles.workMeta}>
          <span className={styles.summaryLabel}>Type</span>
          <TypeChainSummary chain={branch.typeChain} />
          <span className={styles.summaryDivider} />
          <span className={styles.summaryLabel}>Targets</span>
          <span className={styles.summaryValue}>
            {branch.trace.target.length}
          </span>
          <span className={styles.summaryLabel}>Post</span>
          <span className={styles.summaryValue}>
            {branch.trace.post.length}
          </span>
          <span className={styles.summaryDivider} />
          <span className={styles.summaryLabel}>Semantics</span>
          <span className={styles.summaryValue}>{attachments.length}</span>
        </div>
      </div>

      <TypeChainView chain={branch.typeChain} />

      <LaneCanvas branch={branch} />

      <div className={styles.lowerGrid}>
        <Panel
          title="Attached semantics"
          meta={`${attachments.length} attached`}
        >
          <SemanticCards attachments={attachments} />
        </Panel>
        <ConnectionLedger branch={branch} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component levels
// ---------------------------------------------------------------------------

function PropertyTable({
  properties,
  onSelect,
}: {
  properties: ProofPropertySummary[];
  onSelect(property: ProofPropertySummary): void;
}) {
  if (!properties.length) {
    return <EmptyState>No properties are declared for this subject.</EmptyState>;
  }
  return (
    <div className={styles.propertyTable}>
      <div className={styles.propertyHead}>
        <span>Property</span>
        <span>Type</span>
        <span>Branches</span>
        <span>Sources</span>
        <span>Bindings</span>
      </div>
      {properties.map((property) => (
        <button
          key={`${property.kind}:${property.component}.${property.property}`}
          type="button"
          className={styles.propertyTableRow}
          onClick={() => onSelect(property)}
        >
          <span className={styles.propertyName}>
            <CircleDot aria-hidden className={styles.propertyDot} />
            {property.property}
          </span>
          <span className={styles.propertyType}>
            {logicalTypeName(property.logicalType)}
          </span>
          <span className={styles.propertyCount}>{property.branchCount}</span>
          <span className={styles.propertySources}>
            {property.sources.join(", ") || "—"}
          </span>
          <span className={styles.propertyBindings}>
            {property.bindingIndexes.join(", ") || "—"}
          </span>
        </button>
      ))}
    </div>
  );
}

function ComponentProofView({
  model,
  actions,
  activity,
}: {
  model: ProofModel;
  actions: FeatureProps["actions"];
  activity: ActivityId;
}) {
  const component = model.component;
  if (!component) {
    return <EmptyState>This component is not present in the blueprint.</EmptyState>;
  }
  const attachments = collectProofSemantics(model);
  return (
    <div className={styles.levelBody}>
      <header className={styles.subjectHeader}>
        <div className={styles.subjectIcon} data-kind={component.kind}>
          {component.kind === "node" ? (
            <Network aria-hidden />
          ) : (
            <GitBranch aria-hidden />
          )}
        </div>
        <div className={styles.subjectCopy}>
          <div className={styles.subjectBadges}>
            <Badge tone="lane">{component.kind}</Badge>
            {component.abstract ? <Badge tone="muted">abstract</Badge> : null}
            {component.labels.map((label) => (
              <Badge key={label} tone="muted">
                {label}
              </Badge>
            ))}
          </div>
          <p className={styles.subjectDescription}>
            {component.description ?? "No description on this declaration."}
          </p>
          {component.provenance ? (
            <p className={styles.subjectProvenance}>
              {component.provenance.source ?? "?"}
              <ArrowRight aria-hidden className={styles.inlineArrow} />
              {component.provenance.target ?? "?"}
            </p>
          ) : null}
        </div>
        <span className={styles.subjectCount}>
          {component.properties.length} properties
        </span>
      </header>

      <Panel title="Properties" meta={`${component.properties.length} rows`}>
        <PropertyTable
          properties={component.properties}
          onSelect={(property) =>
            actions.setSelection(
              activity,
              toWorkbenchSelection({
                level: "property",
                kind: property.kind,
                component: property.component,
                property: property.property,
                propertyRef: property.propertyRef,
              }, activity),
            )
          }
        />
      </Panel>

      <Panel title="Attached semantics" meta={`${attachments.length} attached`}>
        <SemanticCards attachments={attachments} />
      </Panel>
    </div>
  );
}

function AbstractProofView({
  model,
  actions,
  activity,
}: {
  model: ProofModel;
  actions: FeatureProps["actions"];
  activity: ActivityId;
}) {
  const abstract = model.abstract;
  if (!abstract) {
    return <EmptyState>No abstract subject is available.</EmptyState>;
  }
  const attachments = collectProofSemantics(model);
  return (
    <div className={styles.levelBody}>
      <header className={styles.subjectHeader}>
        <div className={styles.subjectIcon} data-kind="abstract">
          <Layers aria-hidden />
        </div>
        <div className={styles.subjectCopy}>
          <div className={styles.subjectBadges}>
            <Badge tone="lane">abstract</Badge>
            {abstract.labels.map((label) => (
              <Badge key={label} tone="muted">
                {label}
              </Badge>
            ))}
          </div>
          <p className={styles.subjectDescription}>
            {abstract.description ?? "No description on this abstract category."}
          </p>
        </div>
        <span className={styles.subjectCount}>
          {abstract.descendants.length} descendants
        </span>
      </header>

      <div className={styles.descendantGrid}>
        {abstract.descendants.map((descendant) => (
          <section key={descendant.name} className={styles.descendantCard}>
            <header>
              <div>
                <h3>{descendant.name}</h3>
                <p>
                  {descendant.description ||
                    descendant.labels.join(", ") ||
                    "No description."}
                </p>
              </div>
              <Badge tone="muted">
                {descendant.properties.length} properties
              </Badge>
            </header>
            <PropertyTable
              properties={descendant.properties}
              onSelect={(property) =>
                actions.setSelection(
                  activity,
                  toWorkbenchSelection({
                    level: "property",
                    kind: property.kind,
                    component: property.component,
                    property: property.property,
                    propertyRef: property.propertyRef,
                  }, activity),
                )
              }
            />
          </section>
        ))}
      </div>

      <Panel title="Attached semantics" meta={`${attachments.length} attached`}>
        <SemanticCards attachments={attachments} />
      </Panel>
    </div>
  );
}

function AssetProofView({
  model,
  actions,
  activity,
}: {
  model: ProofModel;
  actions: FeatureProps["actions"];
  activity: ActivityId;
}) {
  const asset = model.asset;
  if (!asset) {
    return <EmptyState>This asset is not present in the blueprint.</EmptyState>;
  }
  const attachments = collectProofSemantics(model);
  const profile = asset.profile;
  return (
    <div className={styles.levelBody}>
      <header className={styles.subjectHeader}>
        <div className={styles.subjectIcon} data-kind="asset">
          <Database aria-hidden />
        </div>
        <div className={styles.subjectCopy}>
          <div className={styles.subjectBadges}>
            <Badge tone="lane">asset</Badge>
            {profile?.authority ? (
              <Badge tone="muted">{profile.authority}</Badge>
            ) : null}
          </div>
          <p className={styles.subjectDescription}>
            {profile?.description ??
              profile?.subject ??
              "No profile is attached to this asset."}
          </p>
          {profile ? (
            <div className={styles.profileGrid}>
              <ProfileField label="Subject" value={profile.subject} />
              <ProfileField label="Coverage" value={profile.coverage} />
              <ProfileField label="Authority" value={profile.authority} />
              <ProfileField label="Basis" value={profile.basis} />
            </div>
          ) : null}
        </div>
        <span className={styles.subjectCount}>
          {asset.relations.length} tables
        </span>
      </header>

      <div className={styles.assetGrid}>
        <Panel title="Tables" meta={`${asset.relations.length}`}>
          <AssetDataRows rows={asset.relations} />
        </Panel>
        <Panel title="Projections" meta={`${asset.projections.length}`}>
          <AssetDataRows rows={asset.projections} />
        </Panel>
      </div>

      <Panel title="Properties resolving to this asset" meta={`${asset.properties.length} rows`}>
        <PropertyTable
          properties={asset.properties}
          onSelect={(property) =>
            actions.setSelection(
              activity,
              toWorkbenchSelection({
                level: "property",
                kind: property.kind,
                component: property.component,
                property: property.property,
                propertyRef: property.propertyRef,
              }, activity),
            )
          }
        />
      </Panel>

      <div className={styles.assetGrid}>
        <Panel title="Fields" meta={`${asset.fields.length}`}>
          {asset.fields.length ? (
            <div className={styles.fieldList}>
              {asset.fields.map((field) => (
                <div key={field.key} className={styles.fieldRow}>
                  <span className={styles.fieldKey}>{field.key}</span>
                  <span className={styles.fieldType}>
                    {logicalTypeName(field.field.logical_type)}
                  </span>
                  <Badge tone="muted">{field.ownerKind}</Badge>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState>No fields resolve to this asset.</EmptyState>
          )}
        </Panel>
        <Panel title="Attached semantics" meta={`${attachments.length} attached`}>
          <SemanticCards attachments={attachments} />
        </Panel>
      </div>
    </div>
  );
}

function ProfileField({ label, value }: { label: string; value?: string }) {
  return (
    <div className={styles.profileField}>
      <span>{label}</span>
      <strong>{value ?? "—"}</strong>
    </div>
  );
}

function AssetDataRows({
  rows,
}: {
  rows: Array<{
    name: string;
    description?: string;
    columns: number;
    semantics: ProofSemantics[];
  }>;
}) {
  if (!rows.length) return <EmptyState>No entries.</EmptyState>;
  return (
    <div className={styles.dataRows}>
      {rows.map((row) => (
        <div key={row.name} className={styles.dataRow}>
          <div>
            <span className={styles.dataName}>{row.name}</span>
            {row.description ? (
              <span className={styles.dataDescription}>{row.description}</span>
            ) : null}
          </div>
          <span className={styles.dataMeta}>{row.columns} columns</span>
          {row.semantics.length ? (
            <Badge tone="muted">{row.semantics.length} attached</Badge>
          ) : null}
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor export
// ---------------------------------------------------------------------------

function subjectMeaning(
  index: FeatureProps["state"]["index"],
  model: ProofModel,
): DesignMeaningValue {
  switch (model.level) {
    case "property":
      if (
        model.subject.kind === "node" ||
        model.subject.kind === "edge"
      ) {
        return propertyMeaning(
          index,
          model.subject.kind,
          model.subject.component,
          model.subject.property ?? "",
        );
      }
      return attachedMeaning(undefined);
    case "node":
    case "edge":
      return componentMeaning(index, model.level, model.subject.component);
    case "abstract":
      return componentMeaning(index, "node", model.subject.component);
    case "asset":
      return attachedMeaning(
        index.assetsByName.get(model.subject.component)?.semantics,
      );
  }
}

export function DetailEditor(props: FeatureProps) {
  const model = useProofModel(props);
  const selection = props.state.functions[props.activity].selection;
  const meaning = subjectMeaning(props.state.index, model);

  useEffect(() => {
    if (selection.kind || selection.component || selection.property) return;
    props.actions.setSelection(
      props.activity,
      toWorkbenchSelection(defaultProofSubject(props.state.index), props.activity),
    );
  }, [props.actions, props.activity, props.state.index, selection]);

  const changeLevel = (level: ProofLevel) => {
    props.actions.setSelection(
      props.activity,
      toWorkbenchSelection(
        proofSubjectForLevel(props.state.index, model.subject, level),
        props.activity,
      ),
    );
  };

  return (
    <div className={styles.root} data-testid="detail-editor">
      <header className={styles.topbar}>
        <div className={styles.titleBlock}>
          <p className={styles.kicker}>
            <BadgeCheck aria-hidden className={styles.kickerIcon} />
            Design · {model.level}
          </p>
          <h1 className={styles.title}>{levelTitle(model)}</h1>
          <p className={styles.subtitle}>{levelSubtitle(model)}</p>
        </div>
        <LevelSelector level={model.level} onChange={changeLevel} />
      </header>

      <div className={styles.body}>
        <section className={styles.meaningPanel} aria-label="Design meaning">
          <header className={styles.meaningPanelHeader}>
            <span className={styles.meaningPanelTitle}>Design meaning</span>
            <span className={styles.meaningPanelMeta}>
              {model.subject.component}
              {model.subject.property ? `.${model.subject.property}` : ""}
            </span>
          </header>
          <DesignMeaning
            claims={meaning.claims}
            frames={meaning.frames}
            emptyText="No meaning is attached to this subject."
          />
        </section>
        {model.level === "property" ? (
          <PropertyProofView model={model} />
        ) : model.level === "asset" ? (
          <AssetProofView model={model} actions={props.actions} activity={props.activity} />
        ) : model.level === "abstract" ? (
          <AbstractProofView model={model} actions={props.actions} activity={props.activity} />
        ) : (
          <ComponentProofView model={model} actions={props.actions} activity={props.activity} />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Bottom panel
// ---------------------------------------------------------------------------

function traceLaneLabel(lane: LineageLane): string {
  return LINEAGE_LANES.find((entry) => entry.id === lane)?.label ?? lane;
}

function TraceEntries({
  title,
  entries,
}: {
  title: string;
  entries: ProofTrace["source"];
}) {
  if (!entries.length) return null;
  return (
    <div className={styles.traceLane}>
      <span className={styles.traceLaneTitle}>{title}</span>
      {entries.map((entry) => (
        <div key={entry.id} className={styles.traceRow}>
          <span className={styles.traceStep} data-lane={entry.lane}>
            {entry.stepId ? entry.stepId.join(" / ") : entry.label}
          </span>
          <span className={styles.traceInstruction}>
            {entry.workflowKind ?? entry.kind}
          </span>
          <span className={styles.traceArtifacts}>
            {entry.artifacts.length
              ? entry.artifacts.map(traceArtifactLabel).slice(0, 2).join(", ")
              : "—"}
          </span>
        </div>
      ))}
    </div>
  );
}

function TraceTab({ model }: { model: ProofModel }) {
  if (model.branches.length) {
    return (
      <div className={styles.trace}>
        {model.branches.map((branch, index) => (
          <section key={branch.key} className={styles.traceBranch}>
            <header>
              <span className={styles.traceBranchIndex}>
                {String(index + 1).padStart(2, "0")}
              </span>
              <span>{branch.label}</span>
            </header>
            <div className={styles.traceLanes}>
              <TraceEntries title={traceLaneLabel("source")} entries={branch.trace.source} />
              <TraceEntries
                title={traceLaneLabel("transformation")}
                entries={branch.trace.transformation}
              />
              <TraceEntries title={traceLaneLabel("binding")} entries={branch.trace.binding} />
              <TraceEntries title={traceLaneLabel("post")} entries={branch.trace.post} />
              <TraceEntries title={traceLaneLabel("target")} entries={branch.trace.target} />
            </div>
          </section>
        ))}
      </div>
    );
  }
  if (model.properties.length) {
    return (
      <div className={styles.trace}>
        <p className={styles.bottomNote}>
          {model.level} level · select a property to trace one binding chain.
        </p>
        <div className={styles.tracePropertyList}>
          {model.properties.slice(0, 40).map((property) => (
            <div
              key={`${property.kind}:${property.component}.${property.property}`}
              className={styles.traceProperty}
            >
              <span className={styles.traceStep}>
                {property.component}.{property.property}
              </span>
              <span className={styles.traceInstruction}>
                {property.branchCount}{" "}
                {property.branchCount === 1 ? "branch" : "branches"}
              </span>
              <span className={styles.traceArtifacts}>
                {property.steps
                  .map((step) => step.join(" / "))
                  .slice(0, 3)
                  .join(" · ") || "no binding step"}
              </span>
            </div>
          ))}
          {model.properties.length > 40 ? (
            <p className={styles.bottomNote}>
              +{model.properties.length - 40} more properties · the Data tab
              carries the full proof.
            </p>
          ) : null}
        </div>
      </div>
    );
  }
  return <EmptyState>No workflow trace for this subject.</EmptyState>;
}

function EvidenceTab({ model }: { model: ProofModel }) {
  const attachments = collectProofSemantics(model);
  const chain = model.typeChain ?? model.branches[0]?.typeChain;
  return (
    <div className={styles.evidenceTab}>
      <header className={styles.evidenceHead}>
        <span>{attachments.length} attached semantics</span>
        {chain ? <TypeChainSummary chain={chain} /> : null}
      </header>
      <SemanticCards attachments={attachments} />
    </div>
  );
}

export function DetailBottom(props: FeatureProps) {
  const model = useProofModel(props);
  const tab = props.state.functions[props.activity].layout.bottomTab || "trace";
  return (
    <div className={styles.bottom} data-testid="detail-bottom" data-tab={tab}>
      {tab === "evidence" ? (
        <EvidenceTab model={model} />
      ) : (
        <TraceTab model={model} />
      )}
    </div>
  );
}
