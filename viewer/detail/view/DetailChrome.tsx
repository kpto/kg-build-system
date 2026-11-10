import type { ReactNode } from "react";
import {
  Boxes,
  CircleDot,
  Database,
  GitBranch,
  Layers,
  Network,
  type LucideIcon,
} from "lucide-react";

import styles from "../detail.module.css";

export type DetailKind =
  | "node"
  | "edge"
  | "property"
  | "asset"
  | "abstract"
  | "step";

const DETAIL_KINDS: Record<
  DetailKind,
  { icon: LucideIcon; label: string }
> = {
  node: { icon: Network, label: "Node" },
  edge: { icon: GitBranch, label: "Edge" },
  property: { icon: CircleDot, label: "Property" },
  asset: { icon: Database, label: "Asset" },
  abstract: { icon: Layers, label: "Abstract category" },
  step: { icon: Boxes, label: "Step" },
};

export interface DetailDocumentProps {
  kind: DetailKind;
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  testId?: string;
  children: ReactNode;
}

/**
 * The shared chrome of a detail document: sticky top bar, title block and one
 * padded body. Node, property, asset, abstract and step documents use the same
 * surface; the banner logo states the document's kind before its title.
 */
export function DetailDocument({
  kind,
  kicker,
  title,
  subtitle,
  testId,
  children,
}: DetailDocumentProps) {
  const detail = DETAIL_KINDS[kind];
  const Icon = detail.icon;
  return (
    <div className={styles.root} data-testid={testId} data-detail-kind={kind}>
      <header className={styles.topbar}>
        <div className={styles.headMain}>
          <div
            className={styles.logo}
            data-kind={kind}
            role="img"
            aria-label={`${detail.label} document`}
            title={detail.label}
          >
            <Icon aria-hidden className={styles.logoIcon} />
          </div>
          <div className={styles.titleBlock}>
            <p className={styles.kicker}>{kicker}</p>
            <h1 className={styles.title}>{title}</h1>
            {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
          </div>
        </div>
      </header>
      <div className={styles.body}>{children}</div>
    </div>
  );
}

export interface DetailPanelProps {
  title: string;
  meta?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function DetailPanel({
  title,
  meta,
  className,
  children,
}: DetailPanelProps) {
  return (
    <section className={`${styles.panel} ${className ?? ""}`}>
      <header className={styles.panelHead}>
        <h2>{title}</h2>
        {meta ? <span className={styles.panelMeta}>{meta}</span> : null}
      </header>
      <div className={styles.panelBody}>{children}</div>
    </section>
  );
}

export function DetailEmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}
