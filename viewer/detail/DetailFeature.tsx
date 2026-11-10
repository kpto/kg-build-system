"use client";

/**
 * Detail document view: one design subject read in full.
 *
 * The sidebar selects a design subject; the editor presents its meaning,
 * properties and, for a property, its provenance. Provenance is a section of
 * this view.
 */

import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
} from "react";
import {
  ArrowRight,
  BadgeCheck,
  ChevronDown,
  ChevronRight,
  Search,
  Waypoints,
} from "lucide-react";

import type { ConceptKind, ConceptReference } from "@/lib/concepts";
import type { WorkspaceProps, SubjectSelection } from "@/workbench/types";
import { documentTitle } from "@/workbench/types";
import { stepKey } from "@/lib/indexes";
import {
  buildWorkflowModel,
  groupWorkflowRows,
  type WorkflowStepRow,
} from "@/workflow/model/WorkflowViewModel";
import {
  getWorkflowUiStore,
  useWorkflowUi,
} from "@/workflow/view/workflowUi";
import { effectiveLicenseForModel } from "@/proof/license";
import { provenanceReferences } from "@/proof/references";
import { ConceptGlyph, ConceptMark } from "@/shared/ui/ConceptMark";
import { ConceptReferenceChip } from "@/shared/ui/ConceptReference";
import { selectionForConceptTarget } from "@/workbench/conceptTarget";
import { activeDocument, documentSelection } from "@/workbench/types";
import type {
  LineageLane,
  SemanticSubjectKind,
  ViewerIndex,
} from "@/lib/types";
import { LINEAGE_LANES } from "@/lib/types";
import { logicalTypeName } from "@/lib/expressions";
import { DetailDocument, DetailPanel } from "./view/DetailChrome";
import { WorkflowProvenanceGraph } from "./view/WorkflowProvenanceGraph";
import { DataItemEditor } from "./DataItemFeature";
import { ContextMenu } from "@/shared/ui/ContextMenu";
import { laneColor } from "@/shared/ui/theme";
import {
  branchLaneNodes,
  buildProof,
  collectProofSemantics,
  defaultProofSubject,
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
import { DesignMeaning } from "@/shared/design/DesignMeaning";
import {
  attachedMeaning,
  componentMeaning,
  propertyMeaning,
  type DesignMeaningValue,
} from "@/shared/design/meaning";
import styles from "./detail.module.css";

// ---------------------------------------------------------------------------
// Selection plumbing
// ---------------------------------------------------------------------------

function toWorkbenchSelection(subject: ProofSubject): SubjectSelection {
  const base: SubjectSelection = {
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

function useProofModel(props: WorkspaceProps): ProofModel {
  const selection = documentSelection(activeDocument(props.state));
  return useMemo(
    () => buildProof(props.state.index, selection),
    [props.state.index, selection],
  );
}


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

function ProvenanceGroup({
  concept,
  label,
  references,
  onOpen,
  testId,
}: {
  concept: ConceptKind;
  label: string;
  references: ConceptReference[];
  onOpen(reference: ConceptReference): void;
  testId: string;
}) {
  return (
    <div className={styles.provenanceGroup} data-testid={testId}>
      <p className={styles.provenanceGroupLabel}>
        <span className={styles.provenanceGroupTitle}>
          <ConceptGlyph concept={concept} className={styles.provenanceGroupIcon} />
          {label}
        </span>
        <span>{references.length}</span>
      </p>
      {references.length ? (
        <div className={styles.provenanceItems}>
          {references.map((reference) => (
            <ConceptReferenceChip
              key={`${reference.concept}:${reference.name}`}
              reference={reference}
              showIcon={false}
              onOpen={
                reference.target ? () => onOpen(reference) : undefined
              }
            />
          ))}
        </div>
      ) : (
        <p className={styles.provenanceEmpty}>None resolved</p>
      )}
    </div>
  );
}

function ProvenanceSection({
  index,
  model,
  onOpen,
}: {
  index: ViewerIndex;
  model: ProofModel;
  onOpen(reference: ConceptReference): void;
}) {
  const provenance = provenanceReferences(index, model);
  const license = effectiveLicenseForModel(index, model);
  const count = (value: number, singular: string) =>
    `${value} ${value === 1 ? singular : `${singular}s`}`;
  return (
    <section
      className={styles.provenance}
      data-testid="detail-provenance"
      aria-label="Provenance"
    >
      <header className={styles.provenanceHead}>
        <span className={styles.provenanceTitle}>
          <ConceptGlyph concept="graph" className={styles.panelIcon} />
          Provenance
        </span>
        <span className={styles.provenanceMeta}>
          {count(provenance.assets.length, "asset")} ·{" "}
          {count(provenance.tables.length, "table")} ·{" "}
          {count(provenance.projections.length, "projection")}
        </span>
      </header>
      <div className={styles.provenanceGrid}>
        <ProvenanceGroup
          concept="asset"
          label="Assets"
          references={provenance.assets}
          onOpen={onOpen}
          testId="detail-provenance-assets"
        />
        <ProvenanceGroup
          concept="table"
          label="Tables"
          references={provenance.tables}
          onOpen={onOpen}
          testId="detail-provenance-tables"
        />
        <ProvenanceGroup
          concept="projection"
          label="Projections"
          references={provenance.projections}
          onOpen={onOpen}
          testId="detail-provenance-projections"
        />
      </div>
      <footer className={styles.provenanceLicense}>
        <span className={styles.provenanceLicenseLabel}>Effective license</span>
        <span
          className={styles.provenanceLicenseValue}
          title={license.licenses.join(" · ") || "No asset declares a licence."}
          data-testid="detail-effective-license"
          data-license-source={license.source}
        >
          {license.value}
        </span>
      </footer>
    </section>
  );
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

function Panel(props: {
  title: string;
  meta?: ReactNode;
  concept?: ConceptKind;
  children: ReactNode;
  className?: string;
}) {
  return <DetailPanel {...props} />;
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
      concept="property"
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
        data-testid={`explorer-group-${id}`}
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
  concept?: ConceptKind;
  active?: boolean;
  abstract?: boolean;
  onSelect(): void;
  onOpenPermanent?(): void;
  onContextMenu?(event: ReactMouseEvent): void;
}

function SidebarRow({
  label,
  meta,
  concept,
  active,
  abstract,
  onSelect,
  onOpenPermanent,
  onContextMenu,
}: SidebarRowProps) {
  return (
    <button
      type="button"
      className={styles.sideRow}
      data-active={active ? "true" : undefined}
      onClick={onSelect}
      onDoubleClick={onOpenPermanent ?? onSelect}
      onContextMenu={onContextMenu}
      title={label}
    >
      {concept ? (
        <ConceptGlyph concept={concept} className={styles.sideRowIcon} />
      ) : null}
      <span className={styles.sideRowLabel}>{label}</span>
      {abstract ? <span className={styles.sideAbstract}>abstract</span> : null}
      {meta ? <span className={styles.sideRowMeta}>{meta}</span> : null}
    </button>
  );
}

export function ExplorerSidebar(props: WorkspaceProps) {
  const { index } = props.state;
  const document = activeDocument(props.state);
  const active = documentSelection(document);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Set<string>>(() => new Set());
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set());
  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        label: string;
        items: Array<{ label: string; hint?: string; run(): void }>;
      }
    | undefined
  >(undefined);
  const normalized = query.trim().toLowerCase();
  const workflowRows = useMemo(() => buildWorkflowModel(index).rows, [index]);
  const filteredWorkflowRows = useMemo(
    () =>
      workflowRows.filter((row) =>
        matches(normalized, row.name, row.component, row.kindLabel),
      ),
    [workflowRows, normalized],
  );
  const workflowGroups = useMemo(
    () => groupWorkflowRows(filteredWorkflowRows),
    [filteredWorkflowRows],
  );
  const activeStepKey =
    active?.kind === "step" && active.stepId ? stepKey(active.stepId) : undefined;
  const activeStepComponent =
    active?.kind === "step"
      ? active.component ?? active.stepId?.[0]
      : undefined;
  const { state: workflowUi } = useWorkflowUi(props.state.snapshot.name);
  const focusedComponent = workflowUi.filters.component;
  const sectionOpen = (id: string) => Boolean(normalized) || open.has(id);
  const workflowSectionOpen = sectionOpen("workflow");

  // Reveal the active workflow context once when it changes. The reveal is a
  // one-shot state change, not a forced open: once the reader collapses the
  // section or group it stays collapsed until the context changes again.
  useEffect(() => {
    if (normalized) return;
    if (focusedComponent === "all" && !activeStepComponent) return;
    setOpen((current) => {
      if (current.has("workflow")) return current;
      const next = new Set(current);
      next.add("workflow");
      return next;
    });
    const component =
      activeStepComponent ??
      (focusedComponent !== "all" ? focusedComponent : undefined);
    if (!component) return;
    const groupKey = `wf:${component}`;
    setExpanded((current) => {
      if (current.has(groupKey)) return current;
      const next = new Set(current);
      next.add(groupKey);
      return next;
    });
  }, [normalized, focusedComponent, activeStepKey, activeStepComponent]);

  // Single-click navigation reuses one preview tab; an explicit open is permanent.
  const select = (next: ProofSubject) => {
    props.actions.openTab({ selection: toWorkbenchSelection(next), preview: true });
  };
  const openPermanent = (next: ProofSubject) => {
    props.actions.openTab({ selection: toWorkbenchSelection(next) });
  };
  const openActions = (
    event: ReactMouseEvent,
    label: string,
    items: Array<{ label: string; hint?: string; run(): void }>,
  ) => {
    event.preventDefault();
    event.stopPropagation();
    setMenu({ x: event.clientX, y: event.clientY, label, items });
  };
  const openMenu = (
    event: ReactMouseEvent,
    label: string,
    run: () => void,
  ) => {
    openActions(event, label, [
      { label: "Go to Detail", hint: "Open document", run },
    ]);
  };
  const goToGraph = (selection: SubjectSelection) => {
    props.actions.showGraph(selection);
  };
  const goToWorkflow = (component: string) => {
    getWorkflowUiStore(props.state.snapshot.name).setComponent(component);
    props.actions.showWorkflow();
  };
  const openStep = (row: WorkflowStepRow, preview: boolean) => {
    props.actions.openTab({
      selection: {
        kind: "step",
        component: row.component,
        name: row.name,
        stepId: row.id,
      },
      preview,
    });
  };
  const openDataItem = (
    kind: "relation" | "projection",
    name: string,
    preview: boolean,
  ) => {
    props.actions.openTab({
      selection: { kind, name, component: name },
      preview,
    });
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
  const tables = index.relations.filter((relation) =>
    matches(normalized, relation.name, relation.description),
  );
  const projections = index.projections.filter((projection) =>
    matches(normalized, projection.name, projection.description),
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
    component: string,
    property?: string,
  ): boolean =>
    active?.level === level &&
    active.component === component &&
    (property === undefined || active.property === property);

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
            isActive(nodeLevel, node.name) ? "true" : undefined
          }
        >
          <button
            type="button"
            className={styles.treeToggle}
            aria-label={`${nodeOpen ? "Collapse" : "Expand"} ${node.name}`}
            aria-expanded={nodeOpen}
            onClick={() => toggleNode(`node:${node.name}`)}
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
            data-testid={node.abstract ? "detail-tree-abstract" : "detail-tree-node"}
            data-concept={node.abstract ? "abstract" : "node"}
            onClick={() =>
              select({
                level: nodeLevel,
                kind: nodeKind,
                component: node.name,
              })
            }
            onDoubleClick={() =>
              openPermanent({
                level: nodeLevel,
                kind: nodeKind,
                component: node.name,
              })
            }
            onContextMenu={(event) =>
              openActions(event, node.name, [
                {
                  label: "Go to Detail",
                  hint: "Open document",
                  run: () =>
                    openPermanent({
                      level: nodeLevel,
                      kind: nodeKind,
                      component: node.name,
                    }),
                },
                {
                  label: "Go to Graph",
                  hint: "Inspect",
                  run: () =>
                    goToGraph({
                      kind: "node",
                      level: nodeLevel,
                      component: node.name,
                      name: node.name,
                    }),
                },
              ])
            }
            title={node.name}
          >
            <ConceptGlyph
              concept={node.abstract ? "abstract" : "node"}
              className={styles.sideRowIcon}
            />
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
                data-testid="detail-tree-property"
                data-active={
                  isActive("property", node.name, property.name)
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
                onDoubleClick={() =>
                  openPermanent({
                    level: "property",
                    kind: "node",
                    component: node.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
                onContextMenu={(event) =>
                  openActions(event, `${node.name}.${property.name}`, [
                    {
                      label: "Go to Detail",
                      hint: "Open document",
                      run: () =>
                        openPermanent({
                          level: "property",
                          kind: "node",
                          component: node.name,
                          property: property.name,
                          propertyRef: property.ref,
                        }),
                    },
                    {
                      label: "Go to Graph",
                      hint: "Inspect",
                      run: () =>
                        goToGraph({
                          kind: "property",
                          level: "property",
                          component: node.name,
                          property: property.name,
                          name: `${node.name}.${property.name}`,
                        }),
                    },
                  ])
                }
              >
                <ConceptGlyph concept="property" className={styles.conceptDot} />
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
            isActive("edge", edge.name) ? "true" : undefined
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
            data-testid="detail-tree-edge"
            onClick={() =>
              select({
                level: "edge",
                kind: "edge",
                component: edge.name,
              })
            }
            onDoubleClick={() =>
              openPermanent({
                level: "edge",
                kind: "edge",
                component: edge.name,
              })
            }
            onContextMenu={(event) =>
              openActions(event, edge.name, [
                {
                  label: "Go to Detail",
                  hint: "Open document",
                  run: () =>
                    openPermanent({
                      level: "edge",
                      kind: "edge",
                      component: edge.name,
                    }),
                },
                {
                  label: "Go to Graph",
                  hint: "Inspect",
                  run: () =>
                    goToGraph({
                      kind: "edge",
                      level: "edge",
                      component: edge.name,
                      name: edge.name,
                    }),
                },
              ])
            }
            title={edge.name}
          >
            <ConceptGlyph concept="edge" className={styles.sideRowIcon} />
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
                  isActive("property", edge.name, property.name)
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
                onDoubleClick={() =>
                  openPermanent({
                    level: "property",
                    kind: "edge",
                    component: edge.name,
                    property: property.name,
                    propertyRef: property.ref,
                  })
                }
                onContextMenu={(event) =>
                  openActions(event, `${edge.name}.${property.name}`, [
                    {
                      label: "Go to Detail",
                      hint: "Open document",
                      run: () =>
                        openPermanent({
                          level: "property",
                          kind: "edge",
                          component: edge.name,
                          property: property.name,
                          propertyRef: property.ref,
                        }),
                    },
                    {
                      label: "Go to Graph",
                      hint: "Inspect",
                      run: () =>
                        goToGraph({
                          kind: "property",
                          level: "property",
                          component: edge.name,
                          property: property.name,
                          name: `${edge.name}.${property.name}`,
                        }),
                    },
                  ])
                }
              >
                <ConceptGlyph concept="property" className={styles.conceptDot} />
                <span>{property.name}</span>
              </button>
            ))}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className={styles.sidebar} data-testid="explorer-sidebar">
      <div className={styles.search}>
        <Search aria-hidden className={styles.searchIcon} />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Filter the design"
          aria-label="Filter the explorer"
          spellCheck={false}
        />
      </div>
      <div className={`${styles.sideScroll} thin-scrollbar`}>
        <SideSection
          id="assets"
          title="Assets"
          count={assets.length}
          open={sectionOpen("assets")}
          onToggle={toggle}
        >
          {assets.map((asset) => (
            <SidebarRow
              key={asset.name}
              label={asset.name}
              concept="asset"
              meta={index.assetProfilesByName.get(asset.name)?.subject}
              active={isActive("asset", asset.name)}
              onSelect={() =>
                select({ level: "asset", kind: "asset", component: asset.name })
              }
              onOpenPermanent={() =>
                openPermanent({
                  level: "asset",
                  kind: "asset",
                  component: asset.name,
                })
              }
              onContextMenu={(event) =>
                openMenu(event, asset.name, () =>
                  openPermanent({
                    level: "asset",
                    kind: "asset",
                    component: asset.name,
                  }),
                )
              }
            />
          ))}
        </SideSection>

        <SideSection
          id="tables"
          title="Tables"
          count={tables.length}
          open={sectionOpen("tables")}
          onToggle={toggle}
        >
          {tables.map((table) => {
            return (
              <SidebarRow
                key={table.name}
                label={table.name}
                concept="table"
                meta={`${table.columns?.length ?? 0} columns`}
                active={
                  active?.kind === "relation" &&
                  active.component === table.name
                }
                onSelect={() => openDataItem("relation", table.name, true)}
                onOpenPermanent={() =>
                  openDataItem("relation", table.name, false)
                }
              />
            );
          })}
        </SideSection>

        <SideSection
          id="projections"
          title="Projections"
          count={projections.length}
          open={sectionOpen("projections")}
          onToggle={toggle}
        >
          {projections.map((projection) => {
            return (
              <SidebarRow
                key={projection.name}
                label={projection.name}
                concept="projection"
                meta={`${projection.columns?.length ?? 0} columns`}
                active={
                  active?.kind === "projection" &&
                  active.component === projection.name
                }
                onSelect={() =>
                  openDataItem("projection", projection.name, true)
                }
                onOpenPermanent={() =>
                  openDataItem("projection", projection.name, false)
                }
              />
            );
          })}
        </SideSection>

        <SideSection
          id="nodes"
          title="Nodes"
          count={concreteNodes.length}
          open={sectionOpen("nodes")}
          onToggle={toggle}
        >
          {concreteNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="abstract"
          title="Abstract"
          count={abstractNodes.length}
          open={sectionOpen("abstract")}
          onToggle={toggle}
        >
          {abstractNodes.map(renderNode)}
        </SideSection>

        <SideSection
          id="edges"
          title="Edges"
          count={edges.length}
          open={sectionOpen("edges")}
          onToggle={toggle}
        >
          {edges.map(renderEdge)}
        </SideSection>

        <SideSection
          id="workflow"
          title="Workflow"
          count={filteredWorkflowRows.length}
          open={workflowSectionOpen}
          onToggle={toggle}
        >
          {workflowGroups.length ? (
            workflowGroups.map((group) => {
              const groupKey = `wf:${group.component}`;
              const groupOpen = normalized ? true : expanded.has(groupKey);
              return (
                <div key={groupKey} className={styles.treeBlock}>
                  <div className={styles.treeRow}>
                    <button
                      type="button"
                      className={styles.treeToggle}
                      aria-label={`${groupOpen ? "Collapse" : "Expand"} ${group.component}`}
                      aria-expanded={groupOpen}
                      data-testid="explorer-workflow-toggle"
                      data-component={group.component}
                      onClick={() => toggleNode(groupKey)}
                    >
                      {groupOpen ? (
                        <ChevronDown aria-hidden className={styles.sideChevron} />
                      ) : (
                        <ChevronRight aria-hidden className={styles.sideChevron} />
                      )}
                    </button>
                    <button
                      type="button"
                      className={styles.treeLabel}
                      data-testid="explorer-workflow-component"
                      data-component={group.component}
                      onClick={() => toggleNode(groupKey)}
                      onContextMenu={(event) =>
                        openActions(event, group.component, [
                          {
                            label: "Go to Workflow",
                            hint: "Show component",
                            run: () => goToWorkflow(group.component),
                          },
                        ])
                      }
                      title={group.component}
                    >
                      <ConceptGlyph
                        concept="workflow"
                        className={styles.sideRowIcon}
                      />
                      <span>{group.component}</span>
                      <span className={styles.treeMeta}>
                        {group.rows.length}
                      </span>
                    </button>
                  </div>
                  {groupOpen ? (
                    <div className={styles.treeChildren}>
                      {group.rows.map((row) => (
                        <button
                          key={row.key}
                          type="button"
                          className={styles.propertyRow}
                          data-testid="explorer-step"
                          data-active={
                            activeStepKey === row.key ? "true" : undefined
                          }
                          onClick={() => openStep(row, true)}
                          onDoubleClick={() => openStep(row, false)}
                          onContextMenu={(event) =>
                            openActions(event, row.name, [
                              {
                                label: "Go to Detail",
                                hint: "Open document",
                                run: () => openStep(row, false),
                              },
                              {
                                label: "Go to Workflow",
                                hint: "Show component",
                                run: () => goToWorkflow(row.component),
                              },
                            ])
                          }
                          title={`${row.component} · ${row.name}`}
                        >
                          <ConceptGlyph
                            concept="step"
                            className={styles.conceptDot}
                          />
                          <span>{row.name}</span>
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              );
            })
          ) : (
            <p className={styles.sideEmpty}>
              No workflow steps match this filter.
            </p>
          )}
        </SideSection>
      </div>

      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          label={menu.label}
          items={menu.items.map((item) => ({
            label: item.label,
            hint: item.hint,
            onSelect: item.run,
          }))}
          onClose={() => setMenu(undefined)}
        />
      ) : null}

      <footer className={styles.sideFooter}>
        <span className={styles.sideFooterLabel}>Selection</span>
        <span className={styles.sideFooterValue}>
          {document.kind === "graph" ? "Graph" : documentTitle(document)}
        </span>
      </footer>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editor header
// ---------------------------------------------------------------------------

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
      concept="edge"
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
          concept="semantics"
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
  onOpenPermanent,
}: {
  properties: ProofPropertySummary[];
  onSelect(property: ProofPropertySummary): void;
  onOpenPermanent(property: ProofPropertySummary): void;
}) {
  const [menu, setMenu] = useState<
    | {
        x: number;
        y: number;
        label: string;
        items: Array<{ label: string; hint?: string; run(): void }>;
      }
    | undefined
  >(undefined);
  if (!properties.length) {
    return <EmptyState>No properties are declared for this subject.</EmptyState>;
  }
  return (
    <div className={styles.propertyTable} data-testid="detail-properties">
      <div className={styles.propertyHead}>
        <span>Property</span>
        <span>Type</span>
        <span>Branches</span>
        <span>Tables</span>
        <span>Bindings</span>
      </div>
      {properties.map((property) => (
        <button
          key={`${property.kind}:${property.component}.${property.property}`}
          type="button"
          className={styles.propertyTableRow}
          data-testid="detail-property"
          onClick={() => onSelect(property)}
          onDoubleClick={() => onOpenPermanent(property)}
          onContextMenu={(event) => {
            event.preventDefault();
            event.stopPropagation();
            setMenu({
              x: event.clientX,
              y: event.clientY,
              label: `${property.component}.${property.property}`,
              items: [
                {
                  label: "Go to Detail",
                  hint: "Open document",
                  run: () => onOpenPermanent(property),
                },
              ],
            });
          }}
        >
          <span className={styles.propertyName}>
            <ConceptGlyph concept="property" className={styles.conceptDot} />
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
      {menu ? (
        <ContextMenu
          x={menu.x}
          y={menu.y}
          label={menu.label}
          items={menu.items.map((item) => ({
            label: item.label,
            hint: item.hint,
            onSelect: item.run,
          }))}
          onClose={() => setMenu(undefined)}
        />
      ) : null}
    </div>
  );
}

function ComponentProofView({
  model,
  actions,
}: {
  model: ProofModel;
  actions: WorkspaceProps["actions"];
}) {
  const component = model.component;
  if (!component) {
    return <EmptyState>This component is not present in the blueprint.</EmptyState>;
  }
  const attachments = collectProofSemantics(model);
  return (
    <div className={styles.levelBody}>
      <header className={styles.subjectHeader}>
        <ConceptMark concept={component.kind} className={styles.subjectIcon} />
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

      <Panel concept="property" title="Properties" meta={`${component.properties.length} rows`}>
        <PropertyTable
          properties={component.properties}
          onSelect={(property) =>
            actions.openTab({
              selection: toWorkbenchSelection({
                level: "property",
                kind: property.kind,
                component: property.component,
                property: property.property,
                propertyRef: property.propertyRef,
              }),
              preview: true,
            })
          }
          onOpenPermanent={(property) =>
            actions.openTab({
              selection: toWorkbenchSelection({
                level: "property",
                kind: property.kind,
                component: property.component,
                property: property.property,
                propertyRef: property.propertyRef,
              }),
            })
          }
        />
      </Panel>

      <Panel concept="semantics" title="Attached semantics" meta={`${attachments.length} attached`}>
        <SemanticCards attachments={attachments} />
      </Panel>
    </div>
  );
}

function AbstractProofView({
  model,
  actions,
}: {
  model: ProofModel;
  actions: WorkspaceProps["actions"];
}) {
  const abstract = model.abstract;
  if (!abstract) {
    return <EmptyState>No abstract subject is available.</EmptyState>;
  }
  const attachments = collectProofSemantics(model);
  return (
    <div className={styles.levelBody}>
      <header className={styles.subjectHeader}>
        <ConceptMark concept="abstract" className={styles.subjectIcon} />
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
                actions.openTab({
                  selection: toWorkbenchSelection({
                    level: "property",
                    kind: property.kind,
                    component: property.component,
                    property: property.property,
                    propertyRef: property.propertyRef,
                  }),
                  preview: true,
                })
              }
              onOpenPermanent={(property) =>
                actions.openTab({
                  selection: toWorkbenchSelection({
                    level: "property",
                    kind: property.kind,
                    component: property.component,
                    property: property.property,
                    propertyRef: property.propertyRef,
                  }),
                })
              }
            />
          </section>
        ))}
      </div>

      <Panel concept="semantics" title="Attached semantics" meta={`${attachments.length} attached`}>
        <SemanticCards attachments={attachments} />
      </Panel>
    </div>
  );
}

function AssetProofView({
  model,
  actions,
}: {
  model: ProofModel;
  actions: WorkspaceProps["actions"];
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
        <ConceptMark concept="asset" className={styles.subjectIcon} />
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
        <Panel concept="table" title="Tables" meta={`${asset.relations.length}`}>
          <AssetDataRows rows={asset.relations} />
        </Panel>
        <Panel concept="projection" title="Projections" meta={`${asset.projections.length}`}>
          <AssetDataRows rows={asset.projections} />
        </Panel>
      </div>

      <Panel concept="property" title="Properties resolving to this asset" meta={`${asset.properties.length} rows`}>
        <PropertyTable
          properties={asset.properties}
          onSelect={(property) =>
            actions.openTab({
              selection: toWorkbenchSelection({
                level: "property",
                kind: property.kind,
                component: property.component,
                property: property.property,
                propertyRef: property.propertyRef,
              }),
              preview: true,
            })
          }
          onOpenPermanent={(property) =>
            actions.openTab({
              selection: toWorkbenchSelection({
                level: "property",
                kind: property.kind,
                component: property.component,
                property: property.property,
                propertyRef: property.propertyRef,
              }),
            })
          }
        />
      </Panel>

      <div className={styles.assetGrid}>
        <Panel concept="field" title="Fields" meta={`${asset.fields.length}`}>
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
        <Panel concept="semantics" title="Attached semantics" meta={`${attachments.length} attached`}>
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
  index: WorkspaceProps["state"]["index"],
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

export function DetailEditor(props: WorkspaceProps) {
  const selection = documentSelection(activeDocument(props.state));
  if (selection?.kind === "relation" || selection?.kind === "projection") {
    return <DataItemEditor {...props} />;
  }
  return <SubjectDetailEditor {...props} />;
}

function SubjectDetailEditor(props: WorkspaceProps) {
  const model = useProofModel(props);
  const selection = documentSelection(activeDocument(props.state));
  const meaning = subjectMeaning(props.state.index, model);

  useEffect(() => {
    if (selection) return;
    props.actions.setSelection(
      toWorkbenchSelection(defaultProofSubject(props.state.index)),
    );
  }, [props.actions, props.state.index, selection]);

  const openReference = (reference: ConceptReference) => {
    if (!reference.target) return;
    const selection = selectionForConceptTarget(reference.target);
    if (!selection) return;
    props.actions.openTab({ selection, preview: true });
  };
  const endpoint = (name?: string): ConceptReference | undefined =>
    name
      ? {
          concept: "node",
          name,
          target: { concept: "node", name },
        }
      : undefined;
  const source = endpoint(model.component?.provenance?.source);
  const target = endpoint(model.component?.provenance?.target);
  const banner =
    model.level === "edge" && (source || target) ? (
      <div className={styles.bannerRelations} aria-label="Edge endpoints">
        <span className={styles.bannerLabel}>source</span>
        {source ? (
          <ConceptReferenceChip
            reference={source}
            onOpen={() => openReference(source)}
          />
        ) : (
          <span className={styles.bannerEmpty}>not resolved</span>
        )}
        <ArrowRight aria-hidden className={styles.bannerArrow} />
        {target ? (
          <ConceptReferenceChip
            reference={target}
            onOpen={() => openReference(target)}
          />
        ) : (
          <span className={styles.bannerEmpty}>not resolved</span>
        )}
        <span className={styles.bannerLabel}>target</span>
      </div>
    ) : undefined;

  return (
    <DetailDocument
      testId="detail-editor"
      concept={model.level}
      kicker={`Design · ${model.level}`}
      title={levelTitle(model)}
      subtitle={levelSubtitle(model)}
      banner={banner}
    >
      {model.level === "property" ||
      model.level === "node" ||
      model.level === "edge" ? (
        <ProvenanceSection
          index={props.state.index}
          model={model}
          onOpen={openReference}
        />
      ) : null}
      {model.level === "property" ||
      model.level === "node" ||
      model.level === "edge" ? (
        <WorkflowProvenanceGraph
          index={props.state.index}
          model={model}
          onOpenStep={(row) =>
            props.actions.openTab({
              selection: {
                kind: "step",
                component: row.component,
                name: row.name,
                stepId: row.id,
              },
            })
          }
        />
      ) : null}
      <section className={styles.meaningPanel} aria-label="Design meaning">
        <header className={styles.meaningPanelHeader}>
          <span className={styles.meaningPanelTitle}>
            <ConceptGlyph concept="semantics" className={styles.panelIcon} />
            Design meaning
          </span>
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
        <AssetProofView model={model} actions={props.actions} />
      ) : model.level === "abstract" ? (
        <AbstractProofView model={model} actions={props.actions} />
      ) : (
        <ComponentProofView model={model} actions={props.actions} />
      )}
    </DetailDocument>
  );
}
