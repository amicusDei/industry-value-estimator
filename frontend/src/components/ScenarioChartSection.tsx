"use client";

import { useState, useMemo } from "react";
import ScenarioSelector from "@/components/ScenarioSelector";
import type { ScenarioId } from "@/components/ScenarioSelector";
import TimeseriesChart from "@/components/charts/TimeseriesChart";
import type { ScenarioForecastRow } from "@/lib/api";

function toTimeStr(year: number, quarter: number): string {
  const month = { 1: "01", 2: "04", 3: "07", 4: "10" }[quarter] || "01";
  return `${year}-${month}-01`;
}

interface Props {
  scenarioData: ScenarioForecastRow[];
  segmentName?: string;
}

export default function ScenarioChartSection({ scenarioData, segmentName }: Props) {
  const [scenario, setScenario] = useState<ScenarioId>("base");

  const { historical, forecast, ci80, ci95 } = useMemo(() => {
    const rows = scenarioData.filter((r) => r.scenario === scenario);

    const historical = rows
      .filter((r) => !r.is_forecast)
      .map((r) => ({ time: toTimeStr(r.year, r.quarter), value: r.point_estimate }));

    const forecast = rows
      .filter((r) => r.is_forecast)
      .map((r) => ({ time: toTimeStr(r.year, r.quarter), value: r.point_estimate }));

    const ci80 = rows
      .filter((r) => r.is_forecast)
      .map((r) => ({ time: toTimeStr(r.year, r.quarter), lower: r.ci80_lower, upper: r.ci80_upper }));

    const ci95 = rows
      .filter((r) => r.is_forecast)
      .map((r) => ({ time: toTimeStr(r.year, r.quarter), lower: r.ci95_lower, upper: r.ci95_upper }));

    return { historical, forecast, ci80, ci95 };
  }, [scenarioData, scenario]);

  return (
    <div className="bg-surface border border-border rounded-lg p-4 mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <h2 className="text-sm font-medium text-muted uppercase tracking-wider">
          Scenario Forecast
        </h2>
        <ScenarioSelector selected={scenario} onChange={setScenario} />
      </div>
      <TimeseriesChart historical={historical} forecast={forecast} ci80={ci80} ci95={ci95} segmentName={segmentName} />
    </div>
  );
}
