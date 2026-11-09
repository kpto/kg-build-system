/**
 * Entry point for the Topology workbench function.
 *
 * The shell imports this module and mounts the three bodies it owns. The
 * implementation lives in the view zone; this file is only the stable feature
 * entry point alongside the workbench activity table.
 */

export {
  TopologyBottom,
  TopologyEditor,
  TopologySidebar,
} from "./view/TopologyFeature";
