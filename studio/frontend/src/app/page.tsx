import { StudioShell } from "@/components/shell/StudioShell";

/**
 * The studio is a single-page tool: this route exists to mount the shell, and the
 * shell owns everything else. Keeping it server-rendered means the document title and
 * the first paint come from the layout, and only the shell is client-side.
 */
export default function Page() {
  return <StudioShell />;
}
