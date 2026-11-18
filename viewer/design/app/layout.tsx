import type { Metadata, Viewport } from "next";

import { themeColor } from "@/shared/ui/theme";
import "./globals.css";

export const metadata: Metadata = {
  title: "KG design viewer",
  description:
    "Visualise the topology and detail of a kg-build-system graph design.",
};

export const viewport: Viewport = {
  colorScheme: "dark",
  themeColor,
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
