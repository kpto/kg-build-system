import { createElement } from "react";

import { registerInspector } from "@/components/shell/inspectorRegistry";
import type { InspectorPanel } from "@/lib/types";
import { parseRef } from "@/lib/ids";
import { TopologyInspector } from "./TopologyInspector";

/**
 * Registration: hand the shell's inspector dock a panel for component refs.
 *
 * The dock renders the highest-priority panel whose `matches` claims a ref, with the
 * shell's generic entity summary at priority 0. Claiming every `component:` ref (whole
 * or part-qualified) above that means selecting a topology vertex — or a slot of one, or
 * a problem badge pointing at either — opens the topology editor's own inspector.
 *
 * This is a `.ts` file (the feature's registration entry point), so the panel element is
 * built with `createElement` rather than JSX.
 */
export const TOPOLOGY_INSPECTOR_ID = "topology.component";

export const topologyInspectorPanel: InspectorPanel = {
  id: TOPOLOGY_INSPECTOR_ID,
  label: "Topology component",
  priority: 10,
  matches: (ref) => parseRef(ref)?.kind === "component",
  render: (props) => createElement(TopologyInspector, props),
};

/** Register the panel; returns the unregister function for the caller's effect. */
export function registerTopologyInspector(): () => void {
  return registerInspector(topologyInspectorPanel);
}
