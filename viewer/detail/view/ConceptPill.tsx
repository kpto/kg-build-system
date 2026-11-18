import type { CSSProperties } from "react";

import type { ConceptKind, ConceptTarget } from "@/lib/concepts";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { useConceptNavigation } from "@/shared/ui/ConceptNavigation";
import { concepts } from "@/shared/ui/concepts";
import styles from "./ConceptPill.module.css";

export interface ConceptPillProps {
  concept: ConceptKind;
  name: string;
  /** The virtual collection this pill opens, when it is a layer. */
  collection?: string;
  /** The owner when a property, field or binding is not unique by name. */
  component?: string;
  /** The property name when the concept is a property. */
  property?: string;
  /** The owner's layer, so a field or binding opens the owner's document. */
  ownerConcept?: ConceptKind;
  /** The step identity, when a step name is not unique across components. */
  stepId?: [string, string];
  /** The binding identity, when a binding name is not unique by component. */
  bindingIndex?: number;
  title?: string;
  active?: boolean;
  className?: string;
  size?: "sm" | "md" | "lg";
}

/**
 * One instance of a layer as an inline pill: the layer's mark, a divider, then
 * the instance name. The pill resolves and opens the instance's document
 * itself through the workbench navigation; a parent supplies identity, never a
 * click handler. Outside the workbench it degrades to a label.
 */
export function ConceptPill({
  concept,
  name,
  collection,
  component,
  property,
  ownerConcept,
  stepId,
  bindingIndex,
  title,
  active = false,
  className,
  size = "sm",
}: ConceptPillProps) {
  const navigation = useConceptNavigation();
  const definition = concepts[concept];
  const style = { "--concept-color": definition.color } as CSSProperties;
  const classes = [
    styles.pill,
    size === "md" && styles.md,
    size === "lg" && styles.lg,
    className,
  ]
    .filter(Boolean)
    .join(" ");
  const target: ConceptTarget = {
    concept,
    name,
    ...(collection ? { collection } : {}),
    ...(component ? { component } : {}),
    ...(property ? { property } : {}),
    ...(ownerConcept ? { ownerConcept } : {}),
    ...(stepId ? { stepId } : {}),
    ...(bindingIndex !== undefined ? { bindingIndex } : {}),
  };
  const body = (
    <>
      <ConceptGlyph concept={concept} className={styles.mark} active={active} />
      <span className={styles.divider} aria-hidden />
      <span className={styles.name}>{name}</span>
    </>
  );

  if (!navigation) {
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
      onClick={() => navigation.open(target)}
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
  return <ConceptPill concept="abstractNode" {...props} />;
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
