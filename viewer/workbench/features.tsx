"use client";

/**
 * Workbench feature registry.
 *
 * Each function owns its sidebar, editor and bottom-panel bodies; the shell owns
 * the snapshot, the stable per-function layout and the selection. This file is
 * the only place that maps an activity id to those bodies.
 */

import { BadgeCheck, Network, ScanSearch, ScrollText } from "lucide-react";

import {
  AuditBottom,
  AuditEditor,
  AuditSidebar,
} from "@/audit/AuditFeature";
import {
  ProofBottom,
  ProofEditor,
  ProofSidebar,
} from "@/proof/ProofFeature";
import {
  SemanticsBottom,
  SemanticsEditor,
  SemanticsSidebar,
} from "@/semantics/SemanticsFeature";
import {
  TopologyBottom,
  TopologyEditor,
  TopologySidebar,
} from "@/topology/TopologyFeature";
import type { ActivityId, FeatureModule } from "./types";

export const FEATURES: FeatureModule[] = [
  {
    id: "semantics",
    label: "Orient",
    icon: ScrollText,
    Sidebar: SemanticsSidebar,
    Editor: SemanticsEditor,
    Bottom: SemanticsBottom,
  },
  {
    id: "audit",
    label: "Audit",
    icon: ScanSearch,
    Sidebar: AuditSidebar,
    Editor: AuditEditor,
    Bottom: AuditBottom,
  },
  {
    id: "proof",
    label: "Proof",
    icon: BadgeCheck,
    Sidebar: ProofSidebar,
    Editor: ProofEditor,
    Bottom: ProofBottom,
  },
  {
    id: "topology",
    label: "Topology",
    icon: Network,
    Sidebar: TopologySidebar,
    Editor: TopologyEditor,
    Bottom: TopologyBottom,
  },
];

export const FEATURE_BY_ID: Record<ActivityId, FeatureModule> = {
  semantics: FEATURES[0],
  audit: FEATURES[1],
  proof: FEATURES[2],
  topology: FEATURES[3],
};

export function getFeature(id: ActivityId): FeatureModule {
  return FEATURE_BY_ID[id];
}
