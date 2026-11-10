import type { ReactNode } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph, ConceptMark } from "@/shared/ui/ConceptMark";
import styles from "../detail.module.css";

export interface DetailDocumentProps {
  concept: ConceptKind;
  kicker: string;
  title: string;
  subtitle?: ReactNode;
  banner?: ReactNode;
  testId?: string;
  children: ReactNode;
}

/**
 * The shared chrome of a detail document: sticky top bar, title block and one
 * padded body. Node, property, asset, abstract and step documents use the same
 * surface; the banner mark comes from the canonical concept registry.
 */
export function DetailDocument({
  concept,
  kicker,
  title,
  subtitle,
  banner,
  testId,
  children,
}: DetailDocumentProps) {
  return (
    <div className={styles.root} data-testid={testId} data-concept={concept}>
      <header className={styles.topbar}>
        <div className={styles.headMain}>
          <ConceptMark concept={concept} className={styles.logo} />
          <div className={styles.titleBlock}>
            <p className={styles.kicker}>{kicker}</p>
            <h1 className={styles.title}>{title}</h1>
            {subtitle ? <p className={styles.subtitle}>{subtitle}</p> : null}
          </div>
        </div>
        {banner ? <div className={styles.bannerExtra}>{banner}</div> : null}
      </header>
      <div className={styles.body}>{children}</div>
    </div>
  );
}

export interface DetailPanelProps {
  title: string;
  meta?: ReactNode;
  concept?: ConceptKind;
  className?: string;
  children: ReactNode;
}

export function DetailPanel({
  title,
  meta,
  concept,
  className,
  children,
}: DetailPanelProps) {
  return (
    <section className={`${styles.panel} ${className ?? ""}`}>
      <header className={styles.panelHead}>
        <h2>
          {concept ? (
            <ConceptGlyph concept={concept} className={styles.panelIcon} />
          ) : null}
          {title}
        </h2>
        {meta ? <span className={styles.panelMeta}>{meta}</span> : null}
      </header>
      <div className={styles.panelBody}>{children}</div>
    </section>
  );
}

export function DetailEmptyState({ children }: { children: ReactNode }) {
  return <p className={styles.empty}>{children}</p>;
}
