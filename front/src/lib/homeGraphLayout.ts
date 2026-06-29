import { graphSpreadScale, SITE_UI_SCALE } from '@/lib/siteScale';

export const TIFFANY = '#0ABAB5';

export const RING1_SLOTS = 4;
export const RING2_SLOTS = 4;
export const MAX_HISTORY = 3;

export const NODE_SCALE = 2.05 * SITE_UI_SCALE;
const SPREAD_SCALE = 2.2 * graphSpreadScale();

export const CENTER_SIZE = Math.round(200 * NODE_SCALE);
export const RING1_SIZE = Math.round(120 * NODE_SCALE);
export const CENTER_HOVER_SIZE = Math.round(108 * NODE_SCALE);
export const RING2_ORBIT_SIZE = Math.round(54 * NODE_SCALE * 1.1);
export const RING2_ORBIT_PLACEHOLDER = Math.round(38 * NODE_SCALE);
export const NESTED_HOVER_ORBIT_SIZE = Math.round(44 * NODE_SCALE * 1.08);
export const NESTED_HOVER_ORBIT_PLACEHOLDER = Math.round(30 * NODE_SCALE);
export const PLACEHOLDER_SIZE = Math.round(88 * NODE_SCALE);

export const RING1_RADIUS = Math.round(220 * SPREAD_SCALE);
export const HOVER_INFLUENCER_RADIUS = Math.round(175 * SPREAD_SCALE);
export const RING2_ORBIT_RADIUS = Math.round(96 * SPREAD_SCALE * 1.15);
export const NESTED_HOVER_ORBIT_RADIUS = Math.round(80 * SPREAD_SCALE * 1.12);
export const HOVER_PAN = 0.5;

export const GRAPH_VIEW_HALF = Math.round(
  (RING1_RADIUS +
    RING2_ORBIT_RADIUS +
    NESTED_HOVER_ORBIT_RADIUS +
    RING2_ORBIT_SIZE) *
    0.9,
);

export const HISTORY_ORIGIN = { x: -400, y: 400 };
export const HISTORY_SIZES = [56, 48, 40].map((s) => Math.round(s * NODE_SCALE));

export const LABEL_SMALL_THRESHOLD = Math.round(90 * NODE_SCALE);

export const PAN_TRANSITION = 'transform 0.55s cubic-bezier(0.25, 0.1, 0.25, 1)';
export const NODE_TRANSITION = 'opacity 0.4s ease, transform 0.55s cubic-bezier(0.25, 0.1, 0.25, 1)';
export const HOVER_CLEAR_MS = 160;
export const SINGLE_CLICK_DELAY_MS = 280;

export const RING1_POSITIONS = Array.from({ length: RING1_SLOTS }, (_, i) => {
  const angle = -Math.PI / 2 + (i * 2 * Math.PI) / RING1_SLOTS;
  return {
    angle,
    x: Math.cos(angle) * RING1_RADIUS,
    y: Math.sin(angle) * RING1_RADIUS,
  };
});

export type RingPosition = { angle: number; x: number; y: number };

/** n узлов равномерно по окружности; первый — сверху (−π/2). */
export function ringPositions(count: number, radius = RING1_RADIUS): RingPosition[] {
  if (count <= 0) return [];
  return Array.from({ length: count }, (_, i) => {
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / count;
    return {
      angle,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    };
  });
}

/**
 * Кольцо 1: при 0 узлах — слоты под заглушки (maxSlots);
 * при 1…maxSlots−1 — только реальные узлы, равномерно по дуге.
 */
export function ring1LayoutPositions(
  nodeCount: number,
  maxSlots = RING1_SLOTS,
  radius = RING1_RADIUS,
): RingPosition[] {
  if (nodeCount <= 0) return ringPositions(maxSlots, radius);
  return ringPositions(Math.min(nodeCount, maxSlots), radius);
}
