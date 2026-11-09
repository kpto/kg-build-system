import { Workbench } from "@/workbench/Workbench";

/**
 * The page is the workbench entry point. The shell owns snapshot loading, the
 * activity switch, stable panel layouts and the review sidecar; each activity
 * owns its side bar, editor and bottom-panel bodies.
 */
export default function Page() {
  return <Workbench />;
}
