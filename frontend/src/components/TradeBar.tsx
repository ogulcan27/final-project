"use client";

import { useState } from "react";

interface Props {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  onTrade: (ticker: string, quantity: number, side: "buy" | "sell") => Promise<void>;
}

/** Market order entry: ticker, quantity, buy / sell. */
export function TradeBar({ ticker, onTickerChange, onTrade }: Props) {
  const [quantity, setQuantity] = useState("1");
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(side: "buy" | "sell") {
    const qty = Number(quantity);
    if (!ticker || !(qty > 0)) {
      setMessage({ text: "Enter a ticker and a positive quantity", ok: false });
      return;
    }
    setBusy(true);
    try {
      await onTrade(ticker.toUpperCase(), qty, side);
      setMessage({ text: `${side === "buy" ? "Bought" : "Sold"} ${qty} ${ticker.toUpperCase()}`, ok: true });
    } catch (err) {
      setMessage({ text: (err as Error).message, ok: false });
    } finally {
      setBusy(false);
    }
  }

  const input = "border border-line bg-bg px-2 py-1 font-mono text-xs outline-none focus:border-blue";
  return (
    <div className="flex items-center gap-2 border border-line bg-panel px-2 py-1.5">
      <span className="text-[11px] font-semibold uppercase tracking-widest text-accent">Trade</span>
      <input
        data-testid="trade-ticker"
        value={ticker}
        onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
        placeholder="Ticker"
        className={`${input} w-24 uppercase`}
      />
      <input
        data-testid="trade-quantity"
        type="number"
        min="0"
        step="any"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        placeholder="Qty"
        className={`${input} w-24`}
      />
      <button
        data-testid="trade-buy"
        disabled={busy}
        onClick={() => submit("buy")}
        className="bg-up/90 px-4 py-1 text-xs font-bold text-bg hover:bg-up disabled:opacity-50"
      >
        BUY
      </button>
      <button
        data-testid="trade-sell"
        disabled={busy}
        onClick={() => submit("sell")}
        className="bg-down/90 px-4 py-1 text-xs font-bold text-bg hover:bg-down disabled:opacity-50"
      >
        SELL
      </button>
      {message && (
        <span data-testid="trade-message" className={`ml-2 truncate text-xs ${message.ok ? "text-up" : "text-down"}`}>
          {message.text}
        </span>
      )}
    </div>
  );
}
