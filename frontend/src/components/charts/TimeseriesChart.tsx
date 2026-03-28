"use client";

import { useEffect, useRef } from "react";
import { createChart, LineSeries, AreaSeries } from "lightweight-charts";
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
        background: { color: "#0a0a0f" },
        textColor: "#64748b",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#ffffff08" },
        horzLines: { color: "#ffffff08" },
      },
      rightPriceScale: { borderColor: "#ffffff12" },
      timeScale: { borderColor: "#ffffff12" },
      crosshair: {
        vertLine: { color: "#ffffff20" },
        horzLine: { color: "#ffffff20" },
      },
    });
    chartRef.current = chart;

    // --- CI bands as stacked areas with background mask ---
    // Layer order (bottom to top):
    //   1. CI95 upper fill (faint orange from top)
    //   2. CI95 lower mask (background color from bottom, erases below lower bound)
    //   3. CI80 upper fill (stronger orange from top)
    //   4. CI80 lower mask (background color from bottom, erases below lower bound)
    // Result: visible corridor between lower and upper bounds.

    const BG = "#0a0a0f";

    if (ci95 && ci95.length > 0) {
      // Fill from top down to upper line
      const s95u = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: "rgba(249,115,22,0.06)",
        bottomColor: "rgba(249,115,22,0.06)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s95u.setData(sorted(ci95.map((d) => ({ time: toTime(d.time), value: d.upper }))));

      // Mask: fill background color from bottom up to lower line
      const s95l = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: BG,
        bottomColor: BG,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s95l.setData(sorted(ci95.map((d) => ({ time: toTime(d.time), value: d.lower }))));
    }

    if (ci80 && ci80.length > 0) {
      const s80u = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: "rgba(249,115,22,0.14)",
        bottomColor: "rgba(249,115,22,0.14)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s80u.setData(sorted(ci80.map((d) => ({ time: toTime(d.time), value: d.upper }))));

      const s80l = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: BG,
        bottomColor: BG,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      s80l.setData(sorted(ci80.map((d) => ({ time: toTime(d.time), value: d.lower }))));
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

    // Forecast line (orange)
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
