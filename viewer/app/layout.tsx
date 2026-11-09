import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KG Audit workbench",
  description:
    "Proof, audit, semantics and topology workbench for kg-build-system snapshots.",
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
