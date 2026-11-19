/**
 * Link geometry for the topology canvas.
 *
 * A link must meet each node surface perpendicularly: the path tangent at an
 * endpoint is radial to the node circle. A self-loop is a true circular arc
 * orthogonal to the node, so it reads as one smooth loop. A parallel link is
 * built in the canonical direction of the unordered node pair and then
 * reversed for the actual edge; two edges between the same pair therefore bow
 * on opposite sides instead of attaching at the same two points.
 */

export interface LinkPoint {
  x: number;
  y: number;
}

export interface LinkNode {
  id: string;
  x?: number;
  y?: number;
}

export interface LinkGeometry {
  path: string;
  x: number;
  y: number;
}

const STRAIGHT = 0.01;

/** A loop circle orthogonal to the node: its centre is at sqrt(r^2 + R^2). */
export function selfLoopPath(
  center: LinkPoint,
  nodeRadius: number,
  angle: number,
): LinkGeometry {
  const loop = Math.max(10, Math.min(32, nodeRadius * 1.4));
  const distance = Math.hypot(nodeRadius, loop);
  const ux = Math.cos(angle);
  const uy = Math.sin(angle);
  const px = -uy;
  const py = ux;
  const along = (nodeRadius * nodeRadius) / distance;
  const half = Math.sqrt(
    Math.max(0, nodeRadius * nodeRadius - along * along),
  );
  const startX = center.x + ux * along + px * half;
  const startY = center.y + uy * along + py * half;
  const endX = center.x + ux * along - px * half;
  const endY = center.y + uy * along - py * half;
  // The major arc is the part outside the node; the minor arc is hidden
  // behind it. The arc arrives at the end point along the node radius.
  return {
    path: `M ${startX} ${startY} A ${loop} ${loop} 0 1 0 ${endX} ${endY}`,
    x: endX,
    y: endY,
  };
}

function straightPath(
  source: LinkPoint,
  target: LinkPoint,
  sourceRadius: number,
  targetRadius: number,
): LinkGeometry {
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const distance = Math.max(0.001, Math.hypot(dx, dy));
  const ux = dx / distance;
  const uy = dy / distance;
  const x = target.x - ux * targetRadius;
  const y = target.y - uy * targetRadius;
  return {
    path: `M ${source.x + ux * sourceRadius} ${
      source.y + uy * sourceRadius
    } L ${x} ${y}`,
    x,
    y,
  };
}

/**
 * The path from `source` to `target`.
 *
 * `spread` separates links that share a node pair: it is the signed fan angle,
 * read in the canonical direction of the unordered pair, so a link and its
 * reverse bow on opposite sides. `selfLoopAngle` places a loop around its node.
 */
export function linkPath(
  source: LinkNode,
  target: LinkNode,
  spread: number,
  sourceRadius: number,
  targetRadius: number,
  selfLoopAngle = 0,
): LinkGeometry {
  const sourcePoint: LinkPoint = { x: source.x ?? 0, y: source.y ?? 0 };
  const targetPoint: LinkPoint = { x: target.x ?? 0, y: target.y ?? 0 };
  if (source.id === target.id) {
    return selfLoopPath(sourcePoint, sourceRadius, selfLoopAngle);
  }
  if (Math.abs(spread) < STRAIGHT) {
    return straightPath(sourcePoint, targetPoint, sourceRadius, targetRadius);
  }

  const forward = source.id <= target.id;
  const a = forward ? sourcePoint : targetPoint;
  const b = forward ? targetPoint : sourcePoint;
  const aRadius = forward ? sourceRadius : targetRadius;
  const bRadius = forward ? targetRadius : sourceRadius;

  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const distance = Math.max(0.001, Math.hypot(dx, dy));
  const base = Math.atan2(dy, dx);
  const fan = Math.max(-1.2, Math.min(1.2, spread));
  const startAngle = base + fan;
  const endAngle = base + Math.PI - fan;
  const startNormalX = Math.cos(startAngle);
  const startNormalY = Math.sin(startAngle);
  const endNormalX = Math.cos(endAngle);
  const endNormalY = Math.sin(endAngle);
  const startX = a.x + startNormalX * aRadius;
  const startY = a.y + startNormalY * aRadius;
  const endX = b.x + endNormalX * bRadius;
  const endY = b.y + endNormalY * bRadius;
  const control = Math.max(16, Math.min(90, distance * 0.36));
  const startControlX = startX + startNormalX * control;
  const startControlY = startY + startNormalY * control;
  const endControlX = endX + endNormalX * control;
  const endControlY = endY + endNormalY * control;

  if (forward) {
    return {
      path: `M ${startX} ${startY} C ${startControlX} ${startControlY}, ${endControlX} ${endControlY}, ${endX} ${endY}`,
      x: endX,
      y: endY,
    };
  }
  return {
    path: `M ${endX} ${endY} C ${endControlX} ${endControlY}, ${startControlX} ${startControlY}, ${startX} ${startY}`,
    x: startX,
    y: startY,
  };
}
