import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KG Studio",
  description: "Visual authoring for kg_build_system knowledge graphs",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="h-full overflow-hidden antialiased">{children}</body>
    </html>
  );
}
