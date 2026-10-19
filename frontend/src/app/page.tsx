"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { Heatmap } from "@/components/Heatmap";
import { LineChart } from "@/components/LineChart";
import { Panel } from "@/components/Panel";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { Watchlist } from "@/components/Watchlist";
import { usePriceStream } from "@/hooks/usePriceStream";
import * as api from "@/lib/api";
import { formatPct, formatPrice, signClass } from "@/lib/format";
import { applyLivePrices, snapshotsToPoints } from "@/lib/portfolio";
import type { Portfolio, Snapshot, WatchlistItem } from "@/lib/types";

const EMPTY_PORTFOLIO: Portfolio = { cash_balance: 0, total_value: 0, unrealized_pnl: 0, positions: [] };
const HISTORY_POLL_MS = 30_000;

const loadAll = () => Promise.all([api.getPortfolio(), api.getHistory(), api.getWatchlist()]);

export default function Terminal() {
  const { prices, history, status } = usePriceStream();
  const [portfolio, setPortfolio] = useState<Portfolio>(EMPTY_PORTFOLIO);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [tradeTicker, setTradeTicker] = useState("");
  const [chatOpen, setChatOpen] = useState(true);

  const apply = useCallback(([p, h, w]: [Portfolio, Snapshot[], WatchlistItem[]]) => {
    setPortfolio(p);
    setSnapshots(h);
    setWatchlist(w);
  }, []);
  const refresh = useCallback(() => loadAll().then(apply), [apply]);

  useEffect(() => {
    loadAll().then(apply).catch(() => {});
    const id = setInterval(() => api.getHistory().then(setSnapshots).catch(() => {}), HISTORY_POLL_MS);
    return () => clearInterval(id);
  }, [apply]);

  const active = selected ?? watchlist[0]?.ticker ?? null;

  const select = (ticker: string) => {
    setSelected(ticker);
    setTradeTicker(ticker);
  };

  const live = useMemo(() => {
    const latest = Object.fromEntries(Object.values(prices).map((e) => [e.ticker, e.price]));
    return applyLivePrices(portfolio, latest);
  }, [portfolio, prices]);

  const pnlPoints = useMemo(() => snapshotsToPoints(snapshots), [snapshots]);

  async function handleTrade(ticker: string, quantity: number, side: "buy" | "sell") {
    await api.trade(ticker, quantity, side);
    await refresh();
  }

  async function handleAdd(ticker: string) {
    await api.addTicker(ticker);
    await refresh();
  }

  async function handleRemove(ticker: string) {
    await api.removeTicker(ticker).catch(() => {});
    if (selected === ticker) setSelected(null);
    await refresh();
  }

  const activePrice = active ? prices[active] : undefined;
  const pnlUp = pnlPoints.length < 2 || pnlPoints[pnlPoints.length - 1].value >= pnlPoints[0].value;

  return (
    <div className="flex h-screen min-h-[640px] flex-col">
      <Header totalValue={live.total_value} cash={live.cash_balance} pnl={live.unrealized_pnl} status={status} />
      <main className="flex min-h-0 flex-1 gap-1 p-1">
        <div className="w-72 shrink-0">
          <Watchlist
            items={watchlist}
            prices={prices}
            history={history}
            selected={active}
            onSelect={select}
            onAdd={handleAdd}
            onRemove={handleRemove}
          />
        </div>

        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <Panel
            className="flex-[3]"
            title={active ?? "Chart"}
            right={
              activePrice && (
                <span className="font-mono text-xs">
                  <span className="mr-2">{formatPrice(activePrice.price)}</span>
                  <span className={signClass(activePrice.change_pct)}>{formatPct(activePrice.change_pct)}</span>
                </span>
              )
            }
          >
            <LineChart
              key={active ?? "none"}
              testId="main-chart"
              data={active ? history[active] ?? [] : []}
              color="#209dd7"
            />
          </Panel>

          <div className="flex min-h-0 flex-[2] gap-1">
            <Panel title="Portfolio Heatmap" className="flex-1">
              <Heatmap positions={live.positions} onSelect={select} />
            </Panel>
            <Panel title="Portfolio Value" className="flex-1">
              <LineChart testId="pnl-chart" data={pnlPoints} color={pnlUp ? "#26c281" : "#ef5350"} />
            </Panel>
          </div>

          <TradeBar ticker={tradeTicker} onTickerChange={setTradeTicker} onTrade={handleTrade} />

          <Panel title="Positions" className="flex-[2]">
            <PositionsTable positions={live.positions} onSelect={select} />
          </Panel>
        </div>

        {chatOpen ? (
          <div className="w-80 shrink-0">
            <ChatPanel onActions={() => refresh().catch(() => {})} onCollapse={() => setChatOpen(false)} />
          </div>
        ) : (
          <button
            onClick={() => setChatOpen(true)}
            className="w-7 shrink-0 border border-line bg-panel text-[11px] font-semibold uppercase tracking-widest text-accent [writing-mode:vertical-rl] hover:bg-panel-2"
          >
            Open FinAlly AI
          </button>
        )}
      </main>
    </div>
  );
}
