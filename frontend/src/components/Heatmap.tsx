import { formatPct } from "@/lib/format";
import { layoutTreemap } from "@/lib/treemap";
import type { Position } from "@/lib/types";

/** Green for profit, red for loss; saturates at +/-5%. */
export function pnlColor(pct: number): string {
  const strength = Math.min(Math.abs(pct) / 5, 1);
  const alpha = (0.18 + strength * 0.62).toFixed(2);
  return pct >= 0 ? `rgb(38 194 129 / ${alpha})` : `rgb(239 83 80 / ${alpha})`;
}

interface Props {
  positions: Position[];
  onSelect: (ticker: string) => void;
}

/** Treemap of positions sized by market value and colored by unrealized P&L %. */
export function Heatmap({ positions, onSelect }: Props) {
  const cells = layoutTreemap(positions.map((p) => ({ weight: p.market_value, data: p })));
  return (
    <div data-testid="heatmap" className="relative h-full w-full">
      {cells.length === 0 && (
        <p className="absolute inset-0 grid place-items-center text-xs text-muted">No positions yet</p>
      )}
      {cells.map(({ x, y, w, h, data: p }) => (
        <button
          key={p.ticker}
          data-testid={`heatmap-cell-${p.ticker}`}
          onClick={() => onSelect(p.ticker)}
          className="absolute flex flex-col items-center justify-center overflow-hidden border border-bg font-mono text-xs"
          style={{
            left: `${x}%`,
            top: `${y}%`,
            width: `${w}%`,
            height: `${h}%`,
            backgroundColor: pnlColor(p.pnl_pct),
          }}
        >
          <span className="font-semibold text-text">{p.ticker}</span>
          <span className="text-[10px] text-text/80">{formatPct(p.pnl_pct)}</span>
        </button>
      ))}
    </div>
  );
}
