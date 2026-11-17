import type { CSSProperties } from "react";

import type { ConceptKind } from "@/lib/concepts";
import { ConceptGlyph } from "./ConceptMark";
import { concepts } from "./concepts";
import styles from "./ConceptPill.module.css";

export interface ConceptPillProps {
  concept: ConceptKind;
  name: string;
  onOpen?(): void;
  title?: string;
  active?: boolean;
  className?: string;
  size?: "sm" | "md";
}

/**
 * One instance of a layer as an inline pill: the layer's mark, a divider, then
 * the instance name. Use it wherever a document names an instance in prose, a
 * table, a connection row or a card. The pill is a button when it opens the
 * instance's document and a plain span inside a row that already navigates.
 */
export function ConceptPill({
  concept,
  name,
  onOpen,
  title,
  active = false,
  className,
  size = "sm",
}: ConceptPillProps) {
  const definition = concepts[concept];
  const style = { "--concept-color": definition.color } as CSSProperties;
  const classes = [styles.pill, size === "md" && styles.md, className]
    .filter(Boolean)
    .join(" ");
  const body = (
    <>
      <ConceptGlyph concept={concept} className={styles.mark} active={active} />
      <span className={styles.divider} aria-hidden />
      <span className={styles.name}>{name}</span>
    </>
  );

  if (!onOpen) {
    return (
      <span
        className={classes}
        style={style}
        data-concept={concept}
        data-active={active || undefined}
        title={title ?? `${definition.label} · ${name}`}
      >
        {body}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={classes}
      style={style}
      data-concept={concept}
      data-active={active || undefined}
      title={title ?? `Open ${definition.label.toLowerCase()} ${name}`}
      aria-label={`Open ${definition.label.toLowerCase()} ${name}`}
      onClick={onOpen}
    >
      {body}
    </button>
  );
}

/** Props for one layer's pill; the concept is fixed by the component. */
export type LayerPillProps = Omit<ConceptPillProps, "concept">;

export function GraphPill(props: LayerPillProps) {
  return <ConceptPill concept="graph" {...props} />;
}

export function AbstractPill(props: LayerPillProps) {
  return <ConceptPill concept="abstract" {...props} />;
}

export function NodePill(props: LayerPillProps) {
  return <ConceptPill concept="node" {...props} />;
}

export function EdgePill(props: LayerPillProps) {
  return <ConceptPill concept="edge" {...props} />;
}

export function PropertyPill(props: LayerPillProps) {
  return <ConceptPill concept="property" {...props} />;
}

export function AssetPill(props: LayerPillProps) {
  return <ConceptPill concept="asset" {...props} />;
}

export function SourceRelationPill(props: LayerPillProps) {
  return <ConceptPill concept="table" {...props} />;
}

export function DerivedRelationPill(props: LayerPillProps) {
  return <ConceptPill concept="projection" {...props} />;
}

export function FieldPill(props: LayerPillProps) {
  return <ConceptPill concept="field" {...props} />;
}

export function BindingPill(props: LayerPillProps) {
  return <ConceptPill concept="binding" {...props} />;
}

export function WorkflowPill(props: LayerPillProps) {
  return <ConceptPill concept="workflow" {...props} />;
}

export function StepPill(props: LayerPillProps) {
  return <ConceptPill concept="step" {...props} />;
}

export function MeaningPill(props: LayerPillProps) {
  return <ConceptPill concept="semantics" {...props} />;
}
