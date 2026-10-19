import { formatMoney, signClass } from "@/lib/format";
import type { ConnectionStatus } from "@/lib/types";

const DOT: Record<ConnectionStatus, string> = {
  connected: "bg-up",
  reconnecting: "bg-accent",
  disconnected: "bg-down",
};

interface Props {
  totalValue: number;
  cash: number;
  pnl: number;
  status: ConnectionStatus;
}

export function Header({ totalValue, cash, pnl, status }: Props) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-8 border-b border-line bg-panel px-4">
      <div className="flex items-baseline">
        <span className="text-lg font-bold tracking-tight text-accent">Fin</span>
        <span className="text-lg font-bold tracking-tight text-text">Ally</span>
        <span className="ml-2 text-[10px] uppercase tracking-widest text-muted">AI Trading Workstation</span>
      </div>
      <div className="ml-auto flex items-center gap-8 font-mono text-sm">
        <Stat label="Total Value">
          <span data-testid="total-value" className="text-text">{formatMoney(totalValue)}</span>
        </Stat>
        <Stat label="Unrealized P&L">
          <span className={signClass(pnl)}>
            {formatMoney(pnl)}
          </span>
        </Stat>
        <Stat label="Cash">
          <span data-testid="cash-balance" className="text-text">{formatMoney(cash)}</span>
        </Stat>
        <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-muted">
          <span
            data-testid="connection-status"
            data-status={status}
            title={status}
            className={`h-2.5 w-2.5 rounded-full ${DOT[status]}`}
          />
          {status}
        </div>
      </div>
    </header>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col items-end leading-tight">
      <span className="text-[10px] uppercase tracking-widest text-muted">{label}</span>
      {children}
    </div>
  );
}
