import type { CSSProperties } from "react";

import type { ConceptKind, ConceptTarget } from "@/lib/concepts";
import { ConceptGlyph } from "@/shared/ui/ConceptMark";
import { useConceptNavigation } from "@/shared/ui/ConceptNavigation";
import { useConceptPreview } from "@/shared/ui/ConceptPreview";
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
  /**
   * Open the hover/focus preview from the pill itself. A parent that previews
   * a larger surface disables this so the preview is not opened twice.
   */
  preview?: boolean;
  /** The id of a preview owned by the parent, for the button description. */
  describedBy?: string;
}

/** The concept target the pill previews and opens. */
export function conceptTargetFor(props: ConceptPillProps): ConceptTarget {
  return {
    concept: props.concept,
    name: props.name,
    ...(props.collection ? { collection: props.collection } : {}),
    ...(props.component ? { component: props.component } : {}),
    ...(props.property ? { property: props.property } : {}),
    ...(props.ownerConcept ? { ownerConcept: props.ownerConcept } : {}),
    ...(props.stepId ? { stepId: props.stepId } : {}),
    ...(props.bindingIndex !== undefined
      ? { bindingIndex: props.bindingIndex }
      : {}),
  };
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
  preview: showPreview = true,
  describedBy,
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
  const target = conceptTargetFor({
    concept,
    name,
    collection,
    component,
    property,
    ownerConcept,
    stepId,
    bindingIndex,
  });
  const preview = useConceptPreview(target);
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
    <>
      <button
        type="button"
        className={classes}
        style={style}
        data-concept={concept}
        data-active={active || undefined}
        title={title ?? `Open ${definition.label.toLowerCase()} ${name}`}
        aria-label={`Open ${definition.label.toLowerCase()} ${name}`}
        aria-describedby={describedBy ?? preview.describedBy}
        onMouseEnter={
          showPreview
            ? (event) => preview.open(event.currentTarget)
            : undefined
        }
        onMouseLeave={showPreview ? preview.scheduleClose : undefined}
        onFocus={
          showPreview
            ? (event) => preview.open(event.currentTarget)
            : undefined
        }
        onBlur={showPreview ? preview.scheduleClose : undefined}
        onClick={() => {
          preview.dismiss();
          navigation.open(target);
        }}
        onMouseDown={(event) => {
          if (event.button === 1) event.preventDefault();
        }}
        onAuxClick={(event) => {
          if (event.button !== 1) return;
          event.preventDefault();
          preview.dismiss();
          navigation.open(target, { background: true });
        }}
      >
        {body}
      </button>
      {showPreview ? preview.popup : null}
    </>
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
