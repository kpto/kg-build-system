"use client";

/**
 * Workbench feature registry.
 *
 * Each function owns its sidebar, editor and bottom-panel bodies; the shell owns
 * the snapshot, the stable per-function layout and the selection. This file is
 * the only place that maps an activity id to those bodies.
 */

import { BadgeCheck, BookOpen, Network } from "lucide-react";

import {
  MeaningBottom,
  MeaningEditor,
  MeaningSidebar,
} from "@/meaning/MeaningFeature";
import {
  ProofBottom,
  ProofEditor,
  ProofSidebar,
} from "@/proof/ProofFeature";
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
    id: "proof",
    label: "Proof",
    icon: BadgeCheck,
    Sidebar: ProofSidebar,
    Editor: ProofEditor,
    Bottom: ProofBottom,
  },
  {
    id: "meaning",
    label: "Meaning",
    icon: BookOpen,
    Sidebar: MeaningSidebar,
    Editor: MeaningEditor,
    Bottom: MeaningBottom,
  },
];

export const FEATURE_BY_ID: Record<ActivityId, FeatureModule> = {
  topology: FEATURES[0],
  proof: FEATURES[1],
  meaning: FEATURES[2],
};

export function getFeature(id: ActivityId): FeatureModule {
  return FEATURE_BY_ID[id];
}
