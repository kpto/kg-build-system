import { Workbench } from "@/workbench/Workbench";

/**
 * The page is the workbench entry point. The shell owns snapshot loading, one
 * panel geometry, the document tab strip and the Topology/Detail side-bar
 * sections.
 */
export default function Page() {
  return <Workbench />;
}
