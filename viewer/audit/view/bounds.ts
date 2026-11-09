/**
 * Bounded mounts are a view decision.
 *
 * The model carries every row it can describe; the view decides how many of
 * those rows exist in the DOM at once. These numbers never enter the model.
 */
export const AUDIT_BOUNDS = {
  findings: 40,
  questions: 12,
  coverage: 120,
  decisions: 60,
};
