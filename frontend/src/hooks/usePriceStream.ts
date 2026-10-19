"use client";

import { useEffect, useState } from "react";
import type { ConnectionStatus, PriceEvent, PricePoint } from "@/lib/types";

const MAX_POINTS = 600;

export interface PriceStream {
  prices: Record<string, PriceEvent>;
  history: Record<string, PricePoint[]>;
  status: ConnectionStatus;
}

/** Append a point, keeping one point per second (the latest) and a bounded buffer. */
export function appendPoint(points: PricePoint[] = [], event: PriceEvent): PricePoint[] {
  const time = Math.floor(event.timestamp);
  const last = points[points.length - 1];
  const next = last && last.time === time ? points.slice(0, -1) : points.slice(-MAX_POINTS + 1);
  return [...next, { time, value: event.price }];
}

/** Subscribe to /api/stream/prices, tracking latest prices, per-ticker history and connection status. */
export function usePriceStream(): PriceStream {
  const [prices, setPrices] = useState<Record<string, PriceEvent>>({});
  const [history, setHistory] = useState<Record<string, PricePoint[]>>({});
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");

  useEffect(() => {
    const source = new EventSource("/api/stream/prices");
    source.onopen = () => setStatus("connected");
    source.onerror = () =>
      setStatus(source.readyState === EventSource.CONNECTING ? "reconnecting" : "disconnected");
    source.onmessage = (msg) => {
      const event: PriceEvent = JSON.parse(msg.data);
      setPrices((prev) => ({ ...prev, [event.ticker]: event }));
      setHistory((prev) => ({ ...prev, [event.ticker]: appendPoint(prev[event.ticker], event) }));
    };
    return () => source.close();
  }, []);

  return { prices, history, status };
}
