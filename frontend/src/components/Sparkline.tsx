import type { PricePoint } from "@/lib/types";

const W = 80;
const H = 24;

/** Tiny SVG line of the prices seen since page load. */
export function Sparkline({ points }: { points: PricePoint[] | undefined }) {
  if (!points || points.length < 2) return <svg width={W} height={H} />;
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const range = Math.max(...values) - min || 1;
  const coords = values
    .map((v, i) => `${(i / (values.length - 1)) * W},${H - 2 - ((v - min) / range) * (H - 4)}`)
    .join(" ");
  const color = values[values.length - 1] >= values[0] ? "var(--color-up)" : "var(--color-down)";
  return (
    <svg width={W} height={H} className="overflow-visible">
      <polyline points={coords} fill="none" stroke={color} strokeWidth={1.25} />
    </svg>
  );
}
