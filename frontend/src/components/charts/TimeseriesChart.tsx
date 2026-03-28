"use client";

import { useEffect, useRef } from "react";
import { createChart, LineSeries, AreaSeries } from "lightweight-charts";
import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";

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

    // CI95 band (widest, lightest)
    if (ci95 && ci95.length > 0) {
      const ci95Upper = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: "rgba(249,115,22,0.05)",
        bottomColor: "transparent",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ci95Upper.setData(ci95.map((d) => ({ time: toTime(d.time), value: d.upper })));

      const ci95Lower = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: "transparent",
        bottomColor: "rgba(249,115,22,0.05)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ci95Lower.setData(ci95.map((d) => ({ time: toTime(d.time), value: d.lower })));
    }

    // CI80 band
    if (ci80 && ci80.length > 0) {
      const ci80Upper = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: "rgba(249,115,22,0.12)",
        bottomColor: "transparent",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ci80Upper.setData(ci80.map((d) => ({ time: toTime(d.time), value: d.upper })));

      const ci80Lower = chart.addSeries(AreaSeries, {
        lineColor: "transparent",
        topColor: "transparent",
        bottomColor: "rgba(249,115,22,0.12)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      ci80Lower.setData(ci80.map((d) => ({ time: toTime(d.time), value: d.lower })));
    }

    // Historical line (grey)
    if (historical.length > 0) {
      const histSeries = chart.addSeries(LineSeries, {
        color: "#64748b",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
      });
      histSeries.setData(historical.map((d) => ({ time: toTime(d.time), value: d.value })));
    }

    // Forecast line (orange)
    if (forecast.length > 0) {
      const fcSeries = chart.addSeries(LineSeries, {
        color: "#f97316",
        lineWidth: 2,
        priceLineVisible: false,
      });
      // Connect to last historical point
      const bridge =
        historical.length > 0
          ? [{ time: toTime(historical[historical.length - 1].time), value: historical[historical.length - 1].value }]
          : [];
      fcSeries.setData([...bridge, ...forecast.map((d) => ({ time: toTime(d.time), value: d.value }))]);
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
