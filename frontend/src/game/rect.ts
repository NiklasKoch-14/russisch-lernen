import type { Hotspot } from "../gameTypes";

/**
 * Ein Anteils-Rechteck als CSS-Position.
 *
 * Gerundet wird, weil Fließkomma sonst durchschlägt: `0.14 * 100` ergibt
 * 14.000000000000002, und genau das stünde im style-Attribut.
 */
export function rectStyle(rect: Hotspot) {
  return {
    left: percent(rect.x),
    top: percent(rect.y),
    width: percent(rect.w),
    height: percent(rect.h),
  };
}

function percent(value: number): string {
  return `${Number((value * 100).toFixed(4))}%`;
}
