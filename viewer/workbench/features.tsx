"use client";

/**
 * Workbench feature registry.
 *
 * Each function owns its sidebar, editor and bottom-panel bodies; the shell owns
 * the snapshot, the stable per-function layout and the selection. This file is
 * the only place that maps an activity id to those bodies.
 */

import { BadgeCheck, Network } from "lucide-react";

import {
  DetailBottom,
  DetailEditor,
  DetailSidebar,
} from "@/detail/DetailFeature";
import {
  TopologyBottom,
  TopologyEditor,
  TopologySidebar,
} from "@/topology/TopologyFeature";
import type { ActivityId, FeatureModule } from "./types";

export const FEATURES: FeatureModule[] = [
  {
    id: "topology",
    label: "Topology",
    icon: Network,
    Sidebar: TopologySidebar,
    Editor: TopologyEditor,
    Bottom: TopologyBottom,
  },
  {
    id: "detail",
    label: "Detail",
    icon: BadgeCheck,
    Sidebar: DetailSidebar,
    Editor: DetailEditor,
    Bottom: DetailBottom,
  },
];

export const FEATURE_BY_ID: Record<ActivityId, FeatureModule> = {
  topology: FEATURES[0],
  detail: FEATURES[1],
};

export function getFeature(id: ActivityId): FeatureModule {
  return FEATURE_BY_ID[id];
}
