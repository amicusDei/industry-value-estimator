"use client";

import { useEffect, useRef, useCallback } from "react";
import { createChart, LineSeries, AreaSeries } from "lightweight-charts";
import type {
  IChartApi,
  ISeriesApi,
  SeriesType,
  UTCTimestamp,
  Time,
  MouseEventParams,
  LineData,
} from "lightweight-charts";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

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
  segmentName?: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const BG_COLOR = "#0f1117";

function toTime(s: string): UTCTimestamp {
  return (new Date(s).getTime() / 1000) as UTCTimestamp;
}

function sorted<T extends { time: UTCTimestamp }>(data: T[]): T[] {
  return [...data].sort((a, b) => (a.time as number) - (b.time as number));
}

/** Format a UTC timestamp as "Q1 2024" */
function formatQuarter(ts: UTCTimestamp): string {
  const d = new Date((ts as number) * 1000);
  const m = d.getUTCMonth(); // 0-indexed
  const q = Math.floor(m / 3) + 1;
  return `Q${q} ${d.getUTCFullYear()}`;
}

/** Short quarter label for X-axis: "Q1'24" */
function formatQuarterShort(ts: UTCTimestamp): string {
  const d = new Date((ts as number) * 1000);
  const m = d.getUTCMonth();
  const q = Math.floor(m / 3) + 1;
  const yr = String(d.getUTCFullYear()).slice(-2);
  return `Q${q}'${yr}`;
}

/** Format value as "$XX.XB" or "$X.XT" */
function fmtUsd(v: number): string {
  if (v >= 1000) return `$${(v / 1000).toFixed(1)}T`;
  if (v >= 100) return `$${v.toFixed(0)}B`;
  return `$${v.toFixed(1)}B`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function TimeseriesChart({
  historical,
  forecast,
  ci80,
  ci95,
  height = 400,
  segmentName,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  // Store series refs for crosshair lookup
  const seriesRefs = useRef<{
    hist?: ISeriesApi<SeriesType>;
    fc?: ISeriesApi<SeriesType>;
    ci80Upper?: ISeriesApi<SeriesType>;
    ci80Lower?: ISeriesApi<SeriesType>;
    ci95Upper?: ISeriesApi<SeriesType>;
    ci95Lower?: ISeriesApi<SeriesType>;
  }>({});

  const crosshairHandler = useCallback(
    (param: MouseEventParams<Time>) => {
      const tooltip = tooltipRef.current;
      const container = containerRef.current;
      if (!tooltip || !container) return;

      if (
        !param.time ||
        !param.point ||
        param.point.x < 0 ||
        param.point.y < 0
      ) {
        tooltip.style.display = "none";
        return;
      }

      const ts = param.time as UTCTimestamp;
      const dateLabel = formatQuarter(ts);

      // Extract values from series data
      const getValue = (
        series: ISeriesApi<SeriesType> | undefined
      ): number | null => {
        if (!series) return null;
        const d = param.seriesData.get(series) as
          | LineData<Time>
          | undefined;
        return d && "value" in d ? (d.value as number) : null;
      };

      const histVal = getValue(seriesRefs.current.hist);
      const fcVal = getValue(seriesRefs.current.fc);
      const ci80U = getValue(seriesRefs.current.ci80Upper);
      const ci80L = getValue(seriesRefs.current.ci80Lower);
      const ci95U = getValue(seriesRefs.current.ci95Upper);
      const ci95L = getValue(seriesRefs.current.ci95Lower);

      const pointVal = histVal ?? fcVal;
      if (pointVal === null) {
        tooltip.style.display = "none";
        return;
      }

      const isForecast = fcVal !== null && histVal === null;

      let html = `<div style="font-size:11px;line-height:1.5;font-family:'JetBrains Mono',monospace;">`;
      if (segmentName) {
        html += `<div style="color:#94a3b8;margin-bottom:2px;">${segmentName}</div>`;
      }
      html += `<div style="color:#cbd5e1;font-weight:600;">${dateLabel}</div>`;
      html += `<div style="color:${isForecast ? "#f97316" : "#94a3b8"};margin-top:3px;">`;
      html += `Point Estimate: <span style="color:#f8fafc;font-weight:600;">${fmtUsd(pointVal)}</span></div>`;

      if (ci80U !== null && ci80L !== null) {
        html += `<div style="color:#fb923c;">CI80: ${fmtUsd(ci80L)} – ${fmtUsd(ci80U)}</div>`;
      }
      if (ci95U !== null && ci95L !== null) {
        html += `<div style="color:#fdba74;">CI95: ${fmtUsd(ci95L)} – ${fmtUsd(ci95U)}</div>`;
      }
      html += `</div>`;

      tooltip.innerHTML = html;
      tooltip.style.display = "block";

      // Position tooltip
      const tooltipWidth = 200;
      const tooltipHeight = tooltip.clientHeight || 100;
      const containerWidth = container.clientWidth;

      let left = param.point.x + 16;
      if (left + tooltipWidth > containerWidth) {
        left = param.point.x - tooltipWidth - 16;
      }
      let top = param.point.y - tooltipHeight / 2;
      if (top < 0) top = 0;
      if (top + tooltipHeight > height) top = height - tooltipHeight;

      tooltip.style.left = `${left}px`;
      tooltip.style.top = `${top}px`;
    },
    [height, segmentName]
  );

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height,
      layout: {
        background: { color: BG_COLOR },
        textColor: "#64748b",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#ffffff08" },
        horzLines: { color: "#ffffff08" },
      },
      rightPriceScale: {
        borderColor: "#ffffff12",
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
      localization: {
        priceFormatter: (price: number) => {
          if (price >= 1000) return `$${(price / 1000).toFixed(1)}T`;
          if (price >= 100) return `$${price.toFixed(0)}B`;
          return `$${price.toFixed(1)}B`;
        },
      },
      timeScale: {
        borderColor: "#ffffff12",
        tickMarkFormatter: (time: Time) => {
          return formatQuarterShort(time as UTCTimestamp);
        },
      },
      crosshair: {
        vertLine: { color: "#ffffff30", labelVisible: false },
        horzLine: { color: "#ffffff30" },
      },
    });
    chartRef.current = chart;

    // Reset series refs
    seriesRefs.current = {};

    /* ---------- CI95 band (outer, faint) ---------- */
    if (ci95 && ci95.length > 0) {
      // Upper fill: fills from upper line down to chart bottom
      const ci95Upper = chart.addSeries(AreaSeries, {
        topColor: "rgba(249,115,22,0.08)",
        bottomColor: "rgba(249,115,22,0.08)",
        lineColor: "transparent",
        lineWidth: 0 as 1,
        lineVisible: false,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci95Upper.setData(
        sorted(
          ci95.map((d) => ({ time: toTime(d.time), value: d.upper }))
        )
      );
      seriesRefs.current.ci95Upper = ci95Upper as ISeriesApi<SeriesType>;

      // Lower mask: fills from lower line down to chart bottom with bg color
      const ci95Lower = chart.addSeries(AreaSeries, {
        topColor: BG_COLOR,
        bottomColor: BG_COLOR,
        lineColor: "transparent",
        lineWidth: 0 as 1,
        lineVisible: false,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci95Lower.setData(
        sorted(
          ci95.map((d) => ({ time: toTime(d.time), value: d.lower }))
        )
      );
      seriesRefs.current.ci95Lower = ci95Lower as ISeriesApi<SeriesType>;
    }

    /* ---------- CI80 band (inner, stronger) ---------- */
    if (ci80 && ci80.length > 0) {
      const ci80Upper = chart.addSeries(AreaSeries, {
        topColor: "rgba(249,115,22,0.25)",
        bottomColor: "rgba(249,115,22,0.25)",
        lineColor: "transparent",
        lineWidth: 0 as 1,
        lineVisible: false,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci80Upper.setData(
        sorted(
          ci80.map((d) => ({ time: toTime(d.time), value: d.upper }))
        )
      );
      seriesRefs.current.ci80Upper = ci80Upper as ISeriesApi<SeriesType>;

      const ci80Lower = chart.addSeries(AreaSeries, {
        topColor: BG_COLOR,
        bottomColor: BG_COLOR,
        lineColor: "transparent",
        lineWidth: 0 as 1,
        lineVisible: false,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ci80Lower.setData(
        sorted(
          ci80.map((d) => ({ time: toTime(d.time), value: d.lower }))
        )
      );
      seriesRefs.current.ci80Lower = ci80Lower as ISeriesApi<SeriesType>;
    }

    /* ---------- Historical line (grey) ---------- */
    if (historical.length > 0) {
      const histSeries = chart.addSeries(LineSeries, {
        color: "#64748b",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        crosshairMarkerBackgroundColor: "#64748b",
        crosshairMarkerBorderColor: "#0f1117",
      });
      histSeries.setData(
        sorted(
          historical.map((d) => ({ time: toTime(d.time), value: d.value }))
        )
      );
      seriesRefs.current.hist = histSeries as ISeriesApi<SeriesType>;
    }

    /* ---------- Forecast line (orange) ---------- */
    if (forecast.length > 0) {
      const fcSeries = chart.addSeries(LineSeries, {
        color: "#f97316",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        crosshairMarkerBackgroundColor: "#f97316",
        crosshairMarkerBorderColor: "#0f1117",
      });
      // Connect forecast to last historical point for continuity
      const lastHist =
        historical.length > 0
          ? [
              {
                time: toTime(historical[historical.length - 1].time),
                value: historical[historical.length - 1].value,
              },
            ]
          : [];
      const fcPoints = forecast
        .map((d) => ({ time: toTime(d.time), value: d.value }))
        .filter(
          (p) => lastHist.length === 0 || p.time > lastHist[0].time
        );
      fcSeries.setData(sorted([...lastHist, ...fcPoints]));
      seriesRefs.current.fc = fcSeries as ISeriesApi<SeriesType>;
    }

    /* ---------- Forecast Start indicator ---------- */
    if (historical.length > 0 && forecast.length > 0) {
      const lastHistValue = historical[historical.length - 1].value;

      // Horizontal dashed price line at the last historical value
      // serves as a visual anchor marking where the forecast begins
      if (seriesRefs.current.hist) {
        const histTyped = seriesRefs.current.hist as ISeriesApi<"Line">;
        histTyped.createPriceLine({
          price: lastHistValue,
          color: "#ffffff18",
          lineWidth: 1,
          lineStyle: 2, // dashed
          axisLabelVisible: false,
          title: "Forecast Start",
        });
      }
    }

    /* ---------- Tooltip via crosshair ---------- */
    chart.subscribeCrosshairMove(crosshairHandler);

    /* ---------- Fit & resize ---------- */
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };

    const ro = new ResizeObserver(handleResize);
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      chart.unsubscribeCrosshairMove(crosshairHandler);
      chart.remove();
    };
  }, [historical, forecast, ci80, ci95, height, crosshairHandler]);

  return (
    <div className="w-full flex flex-col gap-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-[2px] bg-[#64748b] rounded-full" />
          Historical
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-[2px] bg-[#f97316] rounded-full" />
          Forecast
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-4 h-2.5 rounded-sm"
            style={{ backgroundColor: "rgba(249,115,22,0.25)" }}
          />
          80% CI
        </span>
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-4 h-2.5 rounded-sm"
            style={{ backgroundColor: "rgba(249,115,22,0.08)" }}
          />
          95% CI
        </span>
      </div>

      {/* Chart container */}
      <div ref={containerRef} className="w-full relative">
        {/* Tooltip overlay */}
        <div
          ref={tooltipRef}
          className="absolute z-10 pointer-events-none rounded border border-slate-700 bg-slate-900/95 px-3 py-2 shadow-lg backdrop-blur-sm"
          style={{ display: "none", minWidth: 180 }}
        />
      </div>
    </div>
  );
}
