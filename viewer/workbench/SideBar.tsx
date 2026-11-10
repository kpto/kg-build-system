"use client";

import { useState } from "react";
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

  const sectionHeader = (
    section: SectionId,
    label: string,
    meta: string,
  ) => {
    const expanded = open === section;
    return (
      <button
        type="button"
        className="wb-side-section-header"
        aria-expanded={expanded}
        onClick={() => toggle(section)}
        data-testid={`sidebar-section-${section}`}
      >
        <ChevronRight
          aria-hidden
          className={cx("size-3 transition-transform", expanded && "rotate-90")}
        />
        <span className="wb-side-section-title">{label}</span>
        <span className="wb-side-section-meta">{meta}</span>
      </button>
    );
  };

  return (
    <aside
      className="wb-sidebar"
      style={{ width: state.layout.sidebarWidth }}
      aria-label="Workbench side bar"
      data-testid="sidebar"
    >
      {sectionHeader(
        "topology",
        "Topology",
        `${stats.topologyNodes}N · ${stats.topologyEdges}E`,
      )}
      {sectionHeader("detail", "Detail", `${stats.topologyNodes} subjects`)}
      <div className="wb-side-section-body thin-scrollbar">
        {open === "topology" ? (
          <TopologySidebar state={state} actions={actions} />
        ) : open === "detail" ? (
          <DetailSidebar state={state} actions={actions} />
        ) : (
          <p className="p-3 text-[10px] text-faint">
            Expand Topology or Detail to work with the design.
          </p>
        )}
      </div>
    </aside>
  );
}
