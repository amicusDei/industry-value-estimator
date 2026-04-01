"use client";

import { useEffect, useState } from "react";
import { getTotalForecasts, ForecastRow } from "@/lib/api";
import TimeseriesChart from "@/components/charts/TimeseriesChart";
import { formatUsdB } from "@/lib/formatters";

function toTimeStr(year: number, quarter: number): string {
  const month = { 1: "01", 2: "04", 3: "07", 4: "10" }[quarter] || "01";
  return `${year}-${month}-01`;
}

export default function TotalChart() {
  const [data, setData] = useState<ForecastRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTotalForecasts("nominal")
      .then((res) => setData(res.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="h-[400px] bg-surface border border-border rounded-lg animate-pulse" />;
  if (data.length === 0) return null;

  const historical = data
    .filter((r) => !r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), value: r.point_estimate }));

  const forecast = data
    .filter((r) => r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), value: r.point_estimate }));

  const ci80 = data
    .filter((r) => r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), lower: r.ci80_lower, upper: r.ci80_upper }));

  const ci95 = data
    .filter((r) => r.is_forecast)
    .map((r) => ({ time: toTimeStr(r.year, r.quarter), lower: r.ci95_lower, upper: r.ci95_upper }));

  const latestHist = historical.length > 0 ? historical[historical.length - 1].value : 0;

  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-lg font-semibold">Total AI Market</h2>
          <p className="text-muted text-xs">
            Current: <span className="font-mono text-text">{formatUsdB(latestHist)}</span> (nominal USD, overlap-adjusted)
          </p>
        </div>
      </div>
      <TimeseriesChart historical={historical} forecast={forecast} ci80={ci80} ci95={ci95} segmentName="Total AI Market" />
    </div>
  );
}
