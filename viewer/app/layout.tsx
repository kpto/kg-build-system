import type { Metadata, Viewport } from "next";
import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "kg-build-system viewer",
  description: "Workflow, blueprint and property-lineage viewer for kg-build-system artifacts.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor: "#1d1d1d",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="ui-grain h-screen overflow-hidden bg-abyss text-ink antialiased">
        {children}
      </body>
    </html>
  );
}
