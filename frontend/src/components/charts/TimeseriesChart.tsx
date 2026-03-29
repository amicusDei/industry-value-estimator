"use client";

import { useEffect, useRef } from "react";
import { createChart, LineSeries } from "lightweight-charts";
import type { IChartApi, UTCTimestamp } from "lightweight-charts";

interface DataPoint {
  time: string;
  value: number;
}

interface CiBand {
  time: string;
  lower: number;
  upper: number;
}

interface Props {
  historical: DataPoint[];
  forecast: DataPoint[];
  ci80?: CiBand[];
  ci95?: CiBand[];
  height?: number;
}

function toTime(s: string): UTCTimestamp {
  return (new Date(s).getTime() / 1000) as UTCTimestamp;
}

function sorted(data: { time: UTCTimestamp; value: number }[]) {
  return [...data].sort((a, b) => (a.time as number) - (b.time as number));
}

export default function TimeseriesChart({
  historical,
  forecast,
  ci80,
  ci95,
  height = 400,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: "#0f1117" },
        textColor: "#64748b",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#ffffff0a" },
        horzLines: { color: "#ffffff0a" },
      },
      rightPriceScale: {
        borderColor: "#ffffff12",
      },
      localization: {
        priceFormatter: (price: number) =>
          price >= 1000 ? `$${(price / 1000).toFixed(1)}T` : `$${price.toFixed(0)}B`,
      },
      timeScale: { borderColor: "#ffffff12" },
      crosshair: {
        vertLine: { color: "#ffffff20" },
        horzLine: { color: "#ffffff20" },
      },
    });
    chartRef.current = chart;

    // --- CI bands as line pairs (upper + lower per level) ---

    // CI95 lines (faint, wider band)
    if (ci95 && ci95.length > 0) {
      const ci95Upper = chart.addSeries(LineSeries, {
        color: "rgba(249,115,22,0.25)",
        lineWidth: 1,
        lineStyle: 2, // dashed
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci95Upper.setData(sorted(ci95.map((d) => ({ time: toTime(d.time), value: d.upper }))));

      const ci95Lower = chart.addSeries(LineSeries, {
        color: "rgba(249,115,22,0.25)",
        lineWidth: 1,
        lineStyle: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci95Lower.setData(sorted(ci95.map((d) => ({ time: toTime(d.time), value: d.lower }))));
    }

    // CI80 lines (stronger, inner band)
    if (ci80 && ci80.length > 0) {
      const ci80Upper = chart.addSeries(LineSeries, {
        color: "rgba(249,115,22,0.50)",
        lineWidth: 1,
        lineStyle: 1, // dotted
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci80Upper.setData(sorted(ci80.map((d) => ({ time: toTime(d.time), value: d.upper }))));

      const ci80Lower = chart.addSeries(LineSeries, {
        color: "rgba(249,115,22,0.50)",
        lineWidth: 1,
        lineStyle: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci80Lower.setData(sorted(ci80.map((d) => ({ time: toTime(d.time), value: d.lower }))));
    }

    // Historical line (grey)
    if (historical.length > 0) {
      const histSeries = chart.addSeries(LineSeries, {
        color: "#64748b",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      histSeries.setData(sorted(historical.map((d) => ({ time: toTime(d.time), value: d.value }))));
    }

    // Forecast line (orange, solid)
    if (forecast.length > 0) {
      const fcSeries = chart.addSeries(LineSeries, {
        color: "#f97316",
        lineWidth: 2,
        priceLineVisible: false,
      });
      const lastHist = historical.length > 0
        ? [{ time: toTime(historical[historical.length - 1].time), value: historical[historical.length - 1].value }]
        : [];
      const fcPoints = forecast
        .map((d) => ({ time: toTime(d.time), value: d.value }))
        .filter((p) => lastHist.length === 0 || p.time > lastHist[0].time);
      fcSeries.setData(sorted([...lastHist, ...fcPoints]));
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [historical, forecast, ci80, ci95, height]);

  return <div ref={containerRef} className="w-full" />;
}
