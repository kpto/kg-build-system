"use client";

import { useEffect } from "react";
import { useUpdateNodeInternals, type Node } from "@xyflow/react";

/**
 * Ask React Flow to re-measure the canvas nodes after mount. Explicit node
 * geometry in the views makes edges available on first paint; this pass keeps
 * React Flow's internal handle bounds in sync for interaction and fitView.
 */
export function FlowInitializer({ nodes }: { nodes: Node[] }) {
  const updateNodeInternals = useUpdateNodeInternals();

  useEffect(() => {
    if (!nodes.length) return;
    const ids = nodes.map((node) => node.id);
    updateNodeInternals(ids);
    const retry = window.setTimeout(() => updateNodeInternals(ids), 120);
    return () => window.clearTimeout(retry);
  }, [nodes, updateNodeInternals]);

  return null;
}
