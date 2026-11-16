"use client";

import {
  useRef,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
  type RefObject,
} from "react";
import { ChevronRight, Search } from "lucide-react";

import { ExplorerSidebar } from "@/detail/DetailFeature";
import { TopologySidebar } from "@/topology/TopologyFeature";
import { WorkflowControls } from "@/workflow/WorkflowFeature";
import { cx } from "@/shared/ui/theme";
import { useWorkbench } from "./store";
import {
  MAX_SIDEBAR_SPLIT,
  MIN_SIDEBAR_SPLIT,
  activeDocument,
  type WorkspaceProps,
  type WorkbenchLayout,
} from "./types";

type SectionId = "control" | "explorer";

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** A ratio separator between two open side-bar sections. */
function SideBarSplitter({
  ratio,
  container,
  onChange,
  onResizeStart,
  onResizeEnd,
}: {
  ratio: number;
  container: RefObject<HTMLElement | null>;
  onChange(value: number): void;
  onResizeStart(): void;
  onResizeEnd(): void;
}) {
  const drag = useRef<{ start: number; ratio: number; height: number } | null>(
    null,
  );

  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (event.button !== 0) return;
    event.preventDefault();
    onResizeStart();
    drag.current = {
      start: event.clientY,
      ratio,
      height: container.current?.getBoundingClientRect().height ?? 600,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    if (!drag.current) return;
    const delta = (event.clientY - drag.current.start) / drag.current.height;
    onChange(clamp(drag.current.ratio + delta, MIN_SIDEBAR_SPLIT, MAX_SIDEBAR_SPLIT));
  };

  const endDrag = (event: PointerEvent<HTMLDivElement>) => {
    drag.current = null;
    onResizeEnd();
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    let next: number | undefined;
    if (event.key === "ArrowUp") next = ratio - 0.03;
    else if (event.key === "ArrowDown") next = ratio + 0.03;
    else if (event.key === "Home") next = MIN_SIDEBAR_SPLIT;
    else if (event.key === "End") next = MAX_SIDEBAR_SPLIT;
    if (next === undefined) return;
    event.preventDefault();
    onChange(clamp(next, MIN_SIDEBAR_SPLIT, MAX_SIDEBAR_SPLIT));
  };

  return (
    <div
      role="separator"
      aria-label="Resize side-bar sections"
      aria-orientation="horizontal"
      aria-valuemin={Math.round(MIN_SIDEBAR_SPLIT * 100)}
      aria-valuemax={Math.round(MAX_SIDEBAR_SPLIT * 100)}
      aria-valuenow={Math.round(ratio * 100)}
      aria-valuetext={`Control ${Math.round(ratio * 100)} percent`}
      tabIndex={0}
      className="wb-splitter"
      data-orientation="horizontal"
      data-testid="sidebar-splitter"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={endDrag}
      onPointerCancel={endDrag}
      onKeyDown={onKeyDown}
    >
      <span className="wb-splitter-grip" aria-hidden />
    </div>
  );
}

function workflowContext(document: ReturnType<typeof activeDocument>): boolean {
  return (
    document.kind === "workflow" ||
    (document.kind === "subject" && document.selection.kind === "step")
  );
}

function ControlBody({ state, actions }: WorkspaceProps) {
  const document = activeDocument(state);
  if (workflowContext(document)) {
    return <WorkflowControls state={state} actions={actions} />;
  }
  if (document.kind === "subject") {
    return (
      <p className="p-3 text-[12px] leading-relaxed text-faint">
        This document has no view controls. Control applies to the Graph and
        Workflow documents.
      </p>
    );
  }
  return <TopologySidebar state={state} actions={actions} />;
}



export function SideBar({ onOpenPalette }: { onOpenPalette(): void }) {
  const { state, actions } = useWorkbench();
  const [open, setOpen] = useState<Record<SectionId, boolean>>({
    control: true,
    explorer: true,
  });
  const [resizing, setResizing] = useState(false);
  const container = useRef<HTMLElement>(null);
  const stats = state.index.stats;
  const document = activeDocument(state);
  const workflow = workflowContext(document);
  const controlMeta = workflow
    ? `${state.index.workflow.steps.length} steps`
    : document.kind === "subject"
      ? "no view"
      : `${stats.topologyNodes}N · ${stats.topologyEdges}E`;
  const explorerMeta = `${stats.topologyNodes} subjects · ${state.index.workflow.steps.length} steps`;
  const bothOpen = open.control && open.explorer;

  const toggle = (section: SectionId) => {
    setOpen((current) => ({ ...current, [section]: !current[section] }));
  };

  const growth = (section: SectionId): number => {
    if (!bothOpen) return 1;
    return section === "control"
      ? state.layout.sidebarSplit
      : 1 - state.layout.sidebarSplit;
  };

  const setSplit = (value: number) => {
    actions.setLayout({ sidebarSplit: value } satisfies Partial<WorkbenchLayout>);
  };

  const section = (
    id: SectionId,
    label: string,
    meta: string,
    body: ReactNode,
  ) => {
    const expanded = open[id];
    return (
      <section
        className="wb-side-section"
        data-open={expanded ? "true" : undefined}
        data-testid={`sidebar-section-body-${id}`}
        style={expanded ? { flexGrow: growth(id) } : undefined}
      >
        <button
          type="button"
          className="wb-side-section-header"
          aria-expanded={expanded}
          onClick={() => toggle(id)}
          data-testid={`sidebar-section-${id}`}
        >
          <ChevronRight
            aria-hidden
            className={cx("size-3 transition-transform", expanded && "rotate-90")}
          />
          <span className="wb-side-section-title">{label}</span>
          <span className="wb-side-section-meta">{meta}</span>
        </button>
        <div
          className="wb-side-section-collapse"
          inert={expanded ? undefined : true}
        >
          <div className="wb-side-section-body thin-scrollbar">{body}</div>
        </div>
      </section>
    );
  };

  return (
    <aside
      ref={container}
      className="wb-sidebar"
      style={{ width: state.layout.sidebarWidth }}
      aria-label="Workbench side bar"
      data-testid="sidebar"
      data-resizing={resizing ? "true" : undefined}
    >

      <div className="wb-side-search">
        <button
          type="button"
          className="wb-side-search-button"
          onClick={onOpenPalette}
          title={state.snapshot.title}
          aria-label={`Search commands and subjects in ${state.snapshot.name}`}
          data-testid="sidebar-command-trigger"
        >
          <Search aria-hidden className="size-3.5" />
          <span className="wb-side-search-name">{state.snapshot.name}</span>
          <kbd className="wb-kbd">Ctrl K</kbd>
        </button>
      </div>
      {section(
        "control",
        "Control",
        controlMeta,
        <ControlBody state={state} actions={actions} />,
      )}
      {bothOpen ? (
        <SideBarSplitter
          ratio={state.layout.sidebarSplit}
          container={container}
          onChange={setSplit}
          onResizeStart={() => setResizing(true)}
          onResizeEnd={() => setResizing(false)}
        />
      ) : null}
      {section(
        "explorer",
        "Explorer",
        explorerMeta,
        <ExplorerSidebar state={state} actions={actions} />,
      )}
    </aside>
  );
}
