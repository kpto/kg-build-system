/**
 * Workflow document view.
 *
 * The Workflow document mounts these bodies. Its filters are part of that
 * document, so the bar sits on the canvas and not in the side bar. The workflow
 * itself is a pinned document: it is a second artifact, not a mode.
 */

export {
  WorkflowControls,
  WorkflowEditor,
  WorkflowStepEditor,
} from "./view/WorkflowFeature";
