"use client";

import { useState, type JSX } from "react";
import { ChevronRight } from "lucide-react";

import { DetailSidebar } from "@/detail/DetailFeature";
import { TopologySidebar } from "@/topology/TopologyFeature";
import { cx } from "@/shared/ui/theme";
import { useWorkbench } from "./store";

type SectionId = "topology" | "detail";

export function SideBar() {
  const { state, actions } = useWorkbench();
  const [open, setOpen] = useState<SectionId | null>("topology");
  const stats = state.index.stats;

  const toggle = (section: SectionId) => {
    setOpen((current) => (current === section ? null : section));
  };

  const section = (
    id: SectionId,
    label: string,
    meta: string,
    Body: () => JSX.Element,
  ) => {
    const expanded = open === id;
    return (
      <section
        className="wb-side-section"
        data-open={expanded ? "true" : undefined}
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
        {expanded ? (
          <div className="wb-side-section-body thin-scrollbar">
            <Body />
          </div>
        ) : null}
      </section>
    );
  };

  return (
    <aside
      className="wb-sidebar"
      style={{ width: state.layout.sidebarWidth }}
      aria-label="Workbench side bar"
      data-testid="sidebar"
    >
      {section(
        "topology",
        "Topology",
        `${stats.topologyNodes}N · ${stats.topologyEdges}E`,
        () => <TopologySidebar state={state} actions={actions} />,
      )}
      {section(
        "detail",
        "Detail",
        `${stats.topologyNodes} subjects`,
        () => <DetailSidebar state={state} actions={actions} />,
      )}
    </aside>
  );
}
