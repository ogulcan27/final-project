"use client";

import { useState, type FormEvent } from "react";
import { formatPct, signClass } from "@/lib/format";
import type { PriceEvent, PricePoint, WatchlistItem } from "@/lib/types";
import { FlashPrice } from "./FlashPrice";
import { Panel } from "./Panel";
import { Sparkline } from "./Sparkline";

interface Props {
  items: WatchlistItem[];
  prices: Record<string, PriceEvent>;
  history: Record<string, PricePoint[]>;
  selected: string | null;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<void>;
  onRemove: (ticker: string) => void;
}

export function Watchlist({ items, prices, history, selected, onSelect, onAdd, onRemove }: Props) {
  const [input, setInput] = useState("");
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    try {
      await onAdd(ticker);
      setInput("");
      setError("");
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <Panel title="Watchlist" right={<span className="text-[10px] text-muted">{items.length}</span>} className="h-full">
      <div className="flex h-full flex-col">
        <form onSubmit={submit} className="flex gap-1 border-b border-line p-2">
          <input
            data-testid="watchlist-add-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Add ticker"
            className="min-w-0 flex-1 border border-line bg-bg px-2 py-1 font-mono text-xs uppercase outline-none focus:border-blue"
          />
          <button
            data-testid="watchlist-add-button"
            type="submit"
            className="bg-purple px-3 text-xs font-semibold text-text hover:brightness-125"
          >
            Add
          </button>
        </form>
        {error && <p className="px-2 py-1 text-xs text-down">{error}</p>}
        <ul className="flex-1 overflow-y-auto">
          {items.map(({ ticker }) => {
            const p = prices[ticker];
            return (
              <li
                key={ticker}
                data-testid={`watchlist-row-${ticker}`}
                onClick={() => onSelect(ticker)}
                className={`group grid cursor-pointer grid-cols-[1rem_3.5rem_1fr_auto] items-center gap-x-2 border-b border-line/50 px-2 py-1.5 hover:bg-panel-2 ${
                  selected === ticker ? "border-l-2 border-l-accent bg-panel-2" : "border-l-2 border-l-transparent"
                }`}
              >
                <button
                  data-testid={`watchlist-remove-${ticker}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemove(ticker);
                  }}
                  title={`Remove ${ticker}`}
                  className="text-xs leading-none text-muted/40 hover:text-down group-hover:text-muted"
                >
                  &times;
                </button>
                <span className="font-mono text-xs font-semibold">{ticker}</span>
                <Sparkline points={history[ticker]} />
                <div className="flex flex-col items-end font-mono text-xs">
                  <FlashPrice price={p?.price} testId={`price-${ticker}`} />
                  <span className={`text-[10px] ${signClass(p?.change_pct)}`}>{formatPct(p?.change_pct)}</span>
                </div>
              </li>
            );
          })}
        </ul>
      </div>
    </Panel>
  );
}
