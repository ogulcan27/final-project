import { formatMoney, formatPct, formatPrice, formatQty, signClass } from "@/lib/format";
import type { Position } from "@/lib/types";

interface Props {
  positions: Position[];
  onSelect: (ticker: string) => void;
}

const HEADERS = ["Ticker", "Qty", "Avg Cost", "Price", "Mkt Value", "Unrl P&L", "%"];

export function PositionsTable({ positions, onSelect }: Props) {
  return (
    <div className="h-full overflow-auto">
      <table data-testid="positions-table" className="w-full font-mono text-xs">
        <thead className="sticky top-0 bg-panel text-[10px] uppercase tracking-wider text-muted">
          <tr>
            {HEADERS.map((h, i) => (
              <th key={h} className={`px-2 py-1 font-normal ${i === 0 ? "text-left" : "text-right"}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr
              key={p.ticker}
              data-testid={`position-row-${p.ticker}`}
              onClick={() => onSelect(p.ticker)}
              className="cursor-pointer border-t border-line/50 hover:bg-panel-2"
            >
              <td className="px-2 py-1 font-semibold">{p.ticker}</td>
              <td className="px-2 py-1 text-right">{formatQty(p.quantity)}</td>
              <td className="px-2 py-1 text-right">{formatPrice(p.avg_cost)}</td>
              <td className="px-2 py-1 text-right">{formatPrice(p.current_price)}</td>
              <td className="px-2 py-1 text-right">{formatMoney(p.market_value)}</td>
              <td className={`px-2 py-1 text-right ${signClass(p.unrealized_pnl)}`}>{formatMoney(p.unrealized_pnl)}</td>
              <td className={`px-2 py-1 text-right ${signClass(p.pnl_pct)}`}>{formatPct(p.pnl_pct)}</td>
            </tr>
          ))}
          {positions.length === 0 && (
            <tr>
              <td colSpan={HEADERS.length} className="px-2 py-4 text-center text-muted">
                No open positions
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
