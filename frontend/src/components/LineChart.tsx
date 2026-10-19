"use client";

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { PricePoint } from "@/lib/types";

interface Props {
  data: PricePoint[];
  color: string;
  testId: string;
}

/** Canvas area chart (Lightweight Charts) that re-renders when `data` changes. */
export function LineChart({ data, color, testId }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);

  useEffect(() => {
    const chart = createChart(containerRef.current!, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#7d8a9c",
        fontSize: 10,
        attributionLogo: false,
      },
      grid: { vertLines: { color: "#1c2533" }, horzLines: { color: "#1c2533" } },
      rightPriceScale: { borderColor: "#263040" },
      timeScale: { borderColor: "#263040", timeVisible: true, secondsVisible: true },
      crosshair: { horzLine: { labelBackgroundColor: "#209dd7" }, vertLine: { labelBackgroundColor: "#209dd7" } },
    });
    chartRef.current = chart;
    seriesRef.current = chart.addSeries(AreaSeries, { lineWidth: 2 });
    return () => chart.remove();
  }, []);

  useEffect(() => {
    seriesRef.current?.applyOptions({
      lineColor: color,
      topColor: `${color}55`,
      bottomColor: `${color}05`,
    });
  }, [color]);

  useEffect(() => {
    seriesRef.current?.setData(data.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    chartRef.current?.timeScale().fitContent();
  }, [data]);

  return <div ref={containerRef} data-testid={testId} className="h-full w-full" />;
}
