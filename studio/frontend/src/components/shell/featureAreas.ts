"use client";

import type { ComponentType } from "react";

import type { FeatureProps, TabArea } from "@/lib/types";
import BindingsFeature from "@/features/bindings/Feature";
import ContractsFeature from "@/features/contracts/Feature";
import ModulesFeature from "@/features/modules/Feature";
import PlanFeature from "@/features/plan/Feature";
import SourcesFeature from "@/features/sources/Feature";
import TopologyFeature from "@/features/topology/Feature";

/**
 * The feature areas the shell renders.
 *
 * A tab maps to exactly one component; `projections` reuses the contracts feature
 * because a projection is a data contract with expression fields, and both tabs are
 * handed the same `FeatureProps`. A feature's local view of which projection or table
 * is open belongs in `selectionStore.setLocalSelection(area, ref)`, not in a prop.
 */
export const FEATURE_AREAS: Readonly<Record<TabArea, ComponentType<FeatureProps>>> = {
  topology: TopologyFeature,
  contracts: ContractsFeature,
  projections: ContractsFeature,
  bindings: BindingsFeature,
  sources: SourcesFeature,
  modules: ModulesFeature,
  plan: PlanFeature,
};
