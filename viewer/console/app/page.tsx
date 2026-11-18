"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  Control,
  Empty,
  Field,
  Hint,
  Label,
  Meta,
  Panel,
  PanelHeader,
  RowButton,
} from "@kbs/design";

import { ConceptMark, ConceptPill, CONCEPTS, conceptFor, conceptForEvent } from "./concepts";
import styles from "./page.module.css";
import { RevisionLineageModal } from "./RevisionLineageModal";

type FieldValue = { label: string; value: string; kind?: string; tone?: string };
type Link = { id: string; kind: string; title?: string; role?: string };
type Entity = {
  id: string;
  kind: string;
  title: string;
  summary?: string;
  created?: string;
  state?: string;
  fields?: FieldValue[];
  links?: Link[];
  view_file?: string;
  message?: string;
};
type EventRef = { kind: string; id: string };
type TimelineEvent = {
  id: string;
  type: string;
  timestamp: string;
  title: string;
  refs?: EventRef[];
  prev?: string[];
  revision_id?: string | null;
  view_file?: string | null;
};
type GraphPayload = { project?: string; objects?: Entity[]; timeline?: TimelineEvent[] };
type ConfigPayload = { viewerUrl?: string; project?: string; dataDir?: string };

const TABS = [
  { id: "viewer", label: "Viewer" },
  { id: "iteration", label: "Iteration" },
  { id: "revisions", label: "Revisions", kind: "revision" },
  { id: "eval_designs", label: "Eval designs", kind: "evaluation_design" },
  { id: "eval_runs", label: "Eval runs", kind: "evaluation_run" },
  { id: "results", label: "Results", kind: "result" },
  { id: "findings", label: "Findings", kind: "finding" },
  { id: "proposals", label: "Proposals", kind: "proposal" },
  { id: "designs", label: "Designs", kind: "change_design" },
] as const;

type TabID = (typeof TABS)[number]["id"];

const EVENT_LABEL: Record<string, string> = {
  design_proposed: "Proposed",
  design_adopted: "Adopted",
  design_rejected: "Rejected",
  design_abandoned: "Abandoned",
  kg_edited: "Revision",
  evaluation_run: "Eval run",
};

const KIND_TAB: Record<string, TabID> = {
  revision: "revisions",
  evaluation_design: "eval_designs",
  evaluation_run: "eval_runs",
  result: "results",
  finding: "findings",
  proposal: "proposals",
  change_design: "designs",
};

function time(value?: string): string {
  const date = new Date(value || "");
  return Number.isNaN(date.getTime()) ? String(value || "") : date.toLocaleString();
}

function short(value?: string): string {
  return String(value || "").replace(/^KG-/, "").slice(0, 12);
}

function shortTime(value?: string): string {
  const date = new Date(value || "");
  if (Number.isNaN(date.getTime())) return String(value || "");
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${pad(date.getMonth() + 1)}/${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function resolveViewer(raw?: string): string {
  const base = raw?.trim() ? raw : "/";
  if (typeof window === "undefined") return base;
  try {
    const url = new URL(base, window.location.href);
    if (["127.0.0.1", "localhost", "0.0.0.0", "[::1]", "::1"].includes(url.hostname)) {
      url.hostname = window.location.hostname;
    }
    return url.toString();
  } catch {
    return "/";
  }
}

/** A revision is one snapshot URL; the viewer reloads on the selected tab. */
function viewerSrc(viewer: string, revision: string | null): string {
  if (!revision || typeof window === "undefined") return viewer;
  try {
    const url = new URL(viewer, window.location.href);
    const snapshot = new URL(
      `/console/api/revision-view?revision=${encodeURIComponent(revision)}`,
      window.location.href,
    );
    url.searchParams.set("snapshot", snapshot.toString());
    return url.toString();
  } catch {
    return viewer;
  }
}

function newestFirst(entities: Entity[]): Entity[] {
  return entities
    .slice()
    .sort((left, right) => {
      const byTime = String(right.created ?? "").localeCompare(String(left.created ?? ""));
      return byTime || String(right.id).localeCompare(String(left.id));
    });
}

function ViewerPane({
  viewer,
  selected,
  revisions,
  onSelect,
}: {
  viewer: string;
  selected: string | null;
  revisions: Entity[];
  onSelect: (revision: string | null) => void;
}) {
  return (
    <Panel className={styles.viewerPanel}>
      <PanelHeader className={styles.viewerHead}>
        <Label>Design viewer</Label>
        <Meta>{selected ? selected : "current"}</Meta>
      </PanelHeader>
      <div className={styles.revisionTimeline} role="tablist" aria-label="Revision timeline">
        <RowButton
          type="button"
          role="tab"
          className={styles.revisionChip}
          data-active={selected === null}
          aria-selected={selected === null}
          onClick={() => onSelect(null)}
        >
          <span>Current</span>
        </RowButton>
        {revisions.map((revision) => (
          <RowButton
            key={revision.id}
            type="button"
            role="tab"
            className={styles.revisionChip}
            data-active={selected === revision.id}
            aria-selected={selected === revision.id}
            onClick={() => onSelect(revision.id)}
          >
            <ConceptMark concept="revision" className={styles.chipMark} />
            <span>{short(revision.id)}</span>
            <Meta>{revision.title}</Meta>
          </RowButton>
        ))}
      </div>
      <div className={styles.viewerBody}>
        <iframe
          className={styles.iframe}
          src={viewerSrc(viewer, selected)}
          title="Knowledge graph design viewer"
          referrerPolicy="no-referrer"
        />
      </div>
    </Panel>
  );
}

function EntityCard({
  entity,
  onOpen,
  onViewRevision,
  onOpenLineage,
  focus,
}: {
  entity: Entity;
  onOpen: (kind: string, id: string) => void;
  onViewRevision: (revision: string) => void;
  onOpenLineage: (revision: string) => void;
  focus: boolean;
}) {
  const concept = conceptFor(entity.kind);
  return (
    <Panel
      className={`${styles.entity} ${focus ? styles.focused : ""}`}
      data-object-id={entity.id}
      style={
        concept
          ? { borderLeftColor: CONCEPTS[concept].color }
          : undefined
      }
    >
      <PanelHeader className={styles.entityHead}>
        {concept ? (
          <ConceptPill concept={concept} />
        ) : (
          <Label>{entity.kind}</Label>
        )}
        <Meta>{time(entity.created)}</Meta>
      </PanelHeader>
      <div className={styles.entityBody}>
        <h2 className={styles.entityTitle}>{entity.title || entity.id}</h2>
        {entity.summary && entity.summary !== entity.title ? (
          <Hint className={styles.entitySummary}>{entity.summary}</Hint>
        ) : null}
        {entity.fields?.length ? (
          <div className={styles.fields}>
            {entity.fields.map((field) => (
              <Field
                key={`${field.label}:${field.value}`}
                label={field.label}
                value={field.kind === "code" ? <Meta>{field.value}</Meta> : field.value}
              />
            ))}
          </div>
        ) : null}
        {entity.kind === "revision" ? (
          <div className={styles.links}>
            {entity.view_file ? (
              <Control type="button" onClick={() => onViewRevision(entity.id)}>
                View snapshot
              </Control>
            ) : null}
            <Control type="button" onClick={() => onOpenLineage(entity.id)}>
              Open lineage
            </Control>
          </div>
        ) : null}
        {entity.links?.length ? (
          <div className={styles.links}>
            <Label>Links</Label>
            {entity.links.map((link) => {
              const linkConcept = conceptFor(link.kind);
              return (
                <RowButton
                  key={`${link.kind}:${link.id}:${link.role ?? ""}`}
                  className={styles.linkRow}
                  type="button"
                  onClick={() => onOpen(link.kind, link.id)}
                  disabled={!KIND_TAB[link.kind]}
                >
                  {linkConcept ? (
                    <ConceptPill
                      concept={linkConcept}
                      label={link.role || undefined}
                    />
                  ) : (
                    <Meta>{link.role || link.kind}</Meta>
                  )}
                  <span>{link.id}</span>
                </RowButton>
              );
            })}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}

function CatalogPane({
  kind,
  label,
  objects,
  focusId,
  onOpen,
  onViewRevision,
  onOpenLineage,
}: {
  kind: string;
  label: string;
  objects: Entity[];
  focusId: string | null;
  onOpen: (kind: string, id: string) => void;
  onViewRevision: (revision: string) => void;
  onOpenLineage: (revision: string) => void;
}) {
  const rows = newestFirst(objects.filter((entity) => entity.kind === kind));
  if (!rows.length) {
    return (
      <Empty className={styles.emptyState}>
        No {label.toLowerCase()} in this notebook.
      </Empty>
    );
  }
  return (
    <div className={styles.catalog} aria-label={label}>
      {rows.map((entity) => (
        <EntityCard
          key={entity.id}
          entity={entity}
          onOpen={onOpen}
          onViewRevision={onViewRevision}
          onOpenLineage={onOpenLineage}
          focus={focusId === entity.id}
        />
      ))}
    </div>
  );
}

function IterationGraph({
  events,
  onOpenLineage,
}: {
  events: TimelineEvent[];
  onOpenLineage: (revision: string) => void;
}) {
  const cardWidth = 260;
  const cardHeight = 120;
  const columnGap = 28;
  const rowGap = 36;
  const padding = 24;

  const byId = new Map(events.map((event) => [event.id, event]));
  const ranks = new Map<string, number>();
  const visiting = new Set<string>();
  const rankOf = (id: string): number => {
    const known = ranks.get(id);
    if (known !== undefined) return known;
    if (visiting.has(id)) return 0;
    visiting.add(id);
    const parents = (byId.get(id)?.prev ?? []).filter((parent) => byId.has(parent));
    const rank = parents.length ? 1 + Math.max(...parents.map(rankOf)) : 0;
    visiting.delete(id);
    ranks.set(id, rank);
    return rank;
  };
  for (const event of events) rankOf(event.id);

  const rows: TimelineEvent[][] = [];
  for (const event of events) {
    const rank = ranks.get(event.id) ?? 0;
    (rows[rank] ??= []).push(event);
  }
  for (const row of rows) {
    row.sort(
      (left, right) =>
        String(left.timestamp).localeCompare(String(right.timestamp)) ||
        left.id.localeCompare(right.id),
    );
  }

  const columns = Math.max(1, ...rows.map((row) => row.length));
  const width = padding * 2 + columns * cardWidth + (columns - 1) * columnGap;
  const height =
    padding * 2 + rows.length * cardHeight + Math.max(0, rows.length - 1) * rowGap;
  const positions = new Map<string, { x: number; y: number }>();
  rows.forEach((row, rank) => {
    const rowWidth = row.length * cardWidth + Math.max(0, row.length - 1) * columnGap;
    const startX = padding + (width - padding * 2 - rowWidth) / 2;
    const y = padding + rank * (cardHeight + rowGap);
    row.forEach((event, index) => {
      positions.set(event.id, {
        x: startX + index * (cardWidth + columnGap),
        y,
      });
    });
  });

  const edges = events.flatMap((event) =>
    (event.prev ?? []).flatMap((parentId) => {
      const parent = positions.get(parentId);
      const child = positions.get(event.id);
      if (!parent || !child || parent.y >= child.y) return [];
      const x1 = parent.x + cardWidth / 2;
      const x2 = child.x + cardWidth / 2;
      const y1 = parent.y + cardHeight;
      const y2 = child.y;
      const middle = (y1 + y2) / 2;
      return [
        <path
          key={`${parentId}:${event.id}`}
          className={styles.edge}
          d={`M ${x1} ${y1} C ${x1} ${middle} ${x2} ${middle} ${x2} ${y2}`}
        />,
      ];
    }),
  );

  if (!events.length) {
    return (
      <Empty className={styles.emptyState}>
        No events yet. Record a finding or a revision to start the iteration.
      </Empty>
    );
  }

  return (
    <Panel className={styles.graphPanel}>
      <PanelHeader className={styles.viewerHead}>
        <Label>Iteration</Label>
        <Meta>{events.length} events</Meta>
      </PanelHeader>
      <div className={styles.graphViewport}>
        <div
          className={styles.graphCanvas}
          style={{ width, height }}
          role="list"
          aria-label="Iteration graph"
        >
          <svg className={styles.graphEdges} width={width} height={height} aria-hidden="true">
            {edges}
          </svg>
          {events.map((event) => {
            const position = positions.get(event.id);
            if (!position) return null;
            const concept = conceptForEvent(event.type);
            return (
              <Panel
                key={event.id}
                className={styles.graphCard}
                data-kind={event.type.replaceAll("_", "-")}
                style={{
                  left: position.x,
                  top: position.y,
                  width: cardWidth,
                  height: cardHeight,
                  borderLeftColor: concept
                    ? CONCEPTS[concept].color
                    : undefined,
                }}
                role="listitem"
              >
                <PanelHeader className={styles.graphCardHead}>
                  {concept ? (
                    <ConceptPill
                      concept={concept}
                      label={
                        EVENT_LABEL[event.type] ??
                        event.type.replaceAll("_", " ")
                      }
                      className={styles.eventPill}
                    />
                  ) : (
                    <Label className={styles.nowrap}>
                      {event.type.replaceAll("_", " ")}
                    </Label>
                  )}
                  <Meta className={styles.nowrap}>{shortTime(event.timestamp)}</Meta>
                </PanelHeader>
                <div className={styles.graphCardBody}>
                  <h3 className={styles.graphCardTitle}>{event.title}</h3>
                  {event.refs?.length ? (
                    <div className={styles.refs} aria-label="Referenced entities">
                      {event.refs.slice(0, 4).map((ref) => (
                        <code key={`${ref.kind}:${ref.id}`}>{ref.id}</code>
                      ))}
                    </div>
                  ) : null}
                  {(() => {
                    const revision =
                      event.revision_id ||
                      event.refs?.find((ref) => ref.kind === "revision")?.id;
                    return revision ? (
                      <Control
                        type="button"
                        className={styles.graphAction}
                        onClick={() => onOpenLineage(revision)}
                      >
                        Open lineage
                      </Control>
                    ) : null;
                  })()}
                </div>
              </Panel>
            );
          })}
        </div>
      </div>
    </Panel>
  );
}

export default function ConsolePage() {
  const [graph, setGraph] = useState<GraphPayload>({});
  const [config, setConfig] = useState<ConfigPayload>({});
  const [active, setActive] = useState<TabID>("viewer");
  const [revisionId, setRevisionId] = useState<string | null>(null);
  const [lineageRevision, setLineageRevision] = useState<string | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const [relationsResponse, configResponse] = await Promise.all([
          fetch("api/relations", { cache: "no-store" }),
          fetch("api/config", { cache: "no-store" }),
        ]);
        if (!relationsResponse.ok) {
          throw new Error(`relations request failed: ${relationsResponse.status}`);
        }
        const [relations, projectConfig] = await Promise.all([
          relationsResponse.json() as Promise<GraphPayload>,
          configResponse.ok
            ? (configResponse.json() as Promise<ConfigPayload>)
            : Promise.resolve({}),
        ]);
        if (!mounted) return;
        setGraph(relations);
        setConfig(projectConfig);
        setLoading(false);
      } catch (reason) {
        if (!mounted) return;
        setError(reason instanceof Error ? reason.message : String(reason));
        setLoading(false);
      }
    }
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!focusId) return;
    const target = document.querySelector(`[data-object-id="${CSS.escape(focusId)}"]`);
    target?.scrollIntoView({ block: "center" });
    setFocusId(null);
  }, [active, focusId]);

  const viewer = useMemo(() => resolveViewer(config.viewerUrl), [config.viewerUrl]);

  const objects = graph.objects ?? [];
  const events = graph.timeline ?? [];
  const revisions = objects
    .filter((object) => object.kind === "revision")
    .sort((left, right) => String(left.created ?? "").localeCompare(String(right.created ?? "")));
  const latest = revisions.at(-1);
  const viewableRevisions = revisions
    .filter((revision) => revision.view_file)
    .slice()
    .reverse();
  const fields = Object.fromEntries((latest?.fields ?? []).map((field) => [field.label, field.value]));
  const project = graph.project || config.project || "project";
  const activeTab = TABS.find((tab) => tab.id === active) ?? TABS[0];
  const activeKind = "kind" in activeTab ? activeTab.kind : undefined;

  const openLink = useCallback((kind: string, id: string) => {
    const tab = KIND_TAB[kind];
    if (!tab) return;
    setActive(tab);
    setFocusId(id);
  }, []);

  const openRevision = useCallback((revision: string) => {
    setRevisionId(revision);
    setActive("viewer");
  }, []);

  const openLineage = useCallback((revision: string) => {
    setLineageRevision(revision);
  }, []);

  return (
    <div className={styles.app}>
      <aside className={styles.rail}>
        <div className={styles.brand}>
          <Label>kbs</Label>
          <strong>console</strong>
        </div>
        <nav className={styles.nav} aria-label="Console views">
          {TABS.map((tab) => {
            const count =
              tab.id === "iteration"
                ? events.length
                : "kind" in tab
                  ? objects.filter((object) => object.kind === tab.kind).length
                  : 0;
            const concept = "kind" in tab ? conceptFor(tab.kind) : null;
            return (
              <RowButton
                key={tab.id}
                type="button"
                className={styles.tab}
                data-active={active === tab.id}
                aria-selected={active === tab.id}
                onClick={() => setActive(tab.id)}
              >
                <span className={styles.tabLabel}>
                  {concept ? (
                    <ConceptMark concept={concept} className={styles.tabMark} />
                  ) : null}
                  <span>{tab.label}</span>
                </span>
                {count ? <Meta>{count}</Meta> : null}
              </RowButton>
            );
          })}
        </nav>
        <div className={styles.facts}>
          <Label>{project} / notebook</Label>
          <span className={styles.revision}>{latest?.title || "Notebook console"}</span>
          <div className={styles.factMeta}>
            <span className={styles.factRevision}>
              <ConceptMark
                concept="revision"
                className={styles.factMark}
              />
              <Meta>rev {short(latest?.id) || "none"}</Meta>
            </span>
            <Meta>{fields["Nodes"] || "0"} nodes</Meta>
            <Meta>{fields["Edges"] || "0"} edges</Meta>
          </div>
        </div>
      </aside>

      <main className={styles.main}>
        <section className={styles.content} aria-label={activeTab.label}>
          {loading ? <Empty className={styles.emptyState}>Loading the notebook catalog…</Empty> : null}
          {error ? (
            <Panel className={styles.viewerPanel}>
              <PanelHeader className={styles.viewerHead}>
                <Label>Notebook API</Label>
                <Meta>unavailable</Meta>
              </PanelHeader>
              <div className={styles.notice}>
                <Hint>{error}</Hint>
                <Hint>
                  Serve the console with <code>kbs console --project .</code>
                </Hint>
                <Control type="button" onClick={() => window.location.reload()}>
                  Retry
                </Control>
              </div>
            </Panel>
          ) : null}
          {!loading && !error && active === "viewer" ? (
            <ViewerPane
              viewer={viewer}
              selected={revisionId}
              revisions={viewableRevisions}
              onSelect={setRevisionId}
            />
          ) : null}
          {!loading && !error && active === "iteration" ? (
            <IterationGraph events={events} onOpenLineage={openLineage} />
          ) : null}
          {!loading && !error && activeKind ? (
            <CatalogPane
              kind={activeKind}
              label={activeTab.label}
              objects={objects}
              focusId={focusId}
              onOpen={openLink}
              onViewRevision={openRevision}
              onOpenLineage={openLineage}
            />
          ) : null}
        </section>
      </main>
      {lineageRevision ? (
        <RevisionLineageModal
          revisionId={lineageRevision}
          objects={objects}
          events={events}
          onOpen={(kind, id) => {
            setLineageRevision(null);
            openLink(kind, id);
          }}
          onClose={() => setLineageRevision(null)}
        />
      ) : null}
    </div>
  );
}
