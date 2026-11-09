import { Workbench } from "@/workbench/Workbench";

/**
 * The page is the workbench entry point. The shell owns snapshot loading, the
 * activity switch and stable panel layouts; each activity owns its side bar,
 * editor and bottom-panel bodies.
 */
export default function Page() {
  return <Workbench />;
}
