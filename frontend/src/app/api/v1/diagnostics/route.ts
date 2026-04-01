import { NextResponse } from 'next/server';
import btData from '@/data/backtesting.json';
import anchorsData from '@/data/anchors.json';

const SEGMENTS = ['ai_hardware', 'ai_infrastructure', 'ai_software', 'ai_adoption'];
const VALID_MODELS = new Set(['prophet_loo', 'ensemble', 'ensemble_loo', 'naive', 'random_walk', 'consensus']);

function buildMapeMatrix(nonSoft: any[]) {
  const prophet = nonSoft.filter((r) => r.model === 'prophet_loo');
  return SEGMENTS.map((seg) => {
    const segRows = prophet.filter((r) => r.segment === seg);
    const entry: Record<string, any> = { segment: seg };
    for (const r of segRows) {
      entry[String(r.year)] = Math.round(r.mape * 10) / 10;
    }
    return entry;
  });
}

function buildCiCoverage(nonSoft: any[]) {
  const prophet = nonSoft.filter((r) => r.model === 'prophet_loo');
  return SEGMENTS.map((seg) => {
    const segRows = prophet.filter((r) => r.segment === seg);
    if (segRows.length === 0) return null;
    const n = segRows.length;
    const ci80Actual = segRows.reduce((s, r) => s + (r.ci80_covered ? 1 : 0), 0) / n;
    const ci95Actual = segRows.reduce((s, r) => s + (r.ci95_covered ? 1 : 0), 0) / n;
    return {
      segment: seg,
      ci80_target: 0.80,
      ci80_actual: Math.round(ci80Actual * 100) / 100,
      ci95_target: 0.95,
      ci95_actual: Math.round(ci95Actual * 100) / 100,
    };
  }).filter(Boolean);
}

function buildRegimeComparison(nonSoft: any[]) {
  const prophet = nonSoft.filter((r) => r.model === 'prophet_loo');
  return SEGMENTS.map((seg) => {
    const segRows = prophet.filter((r) => r.segment === seg);
    const pre = segRows.filter((r) => r.year <= 2021);
    const post = segRows.filter((r) => r.year >= 2022);
    const avg = (arr: any[]) => arr.length > 0 ? Math.round(arr.reduce((s, r) => s + r.mape, 0) / arr.length * 10) / 10 : null;
    return {
      segment: seg,
      pre_genai_mape: avg(pre),
      post_genai_mape: avg(post),
    };
  });
}

function buildDataSources(anchors: any[]) {
  const q4 = anchors.filter((r) => r.quarter === 4 && r.n_sources > 0);
  const sourceInfo: Record<string, { segments: Set<string>; years: Set<number>; n_entries: number }> = {};

  for (const r of q4) {
    const sources = String(r.source_list || '').split(',').map((s: string) => s.trim()).filter(Boolean);
    for (const src of sources) {
      if (!sourceInfo[src]) {
        sourceInfo[src] = { segments: new Set(), years: new Set(), n_entries: 0 };
      }
      sourceInfo[src].segments.add(r.segment);
      sourceInfo[src].years.add(r.estimate_year);
      sourceInfo[src].n_entries += 1;
    }
  }

  return Object.entries(sourceInfo)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, info]) => {
      const years = Array.from(info.years).sort();
      return {
        source_name: name,
        segments_covered: Array.from(info.segments).sort(),
        years_covered: years.length > 1 ? `${years[0]}-${years[years.length - 1]}` : String(years[0]),
        n_entries: info.n_entries,
      };
    });
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const modelFilter = searchParams.get('model');
  const segmentFilter = searchParams.get('segment');

  const allBt = btData as any[];

  // Filter out circular soft actuals
  const nonSoft = allBt.filter((r) => r.actual_type !== 'soft');

  let filtered = nonSoft;
  if (modelFilter) {
    filtered = filtered.filter((r) => r.model === modelFilter);
  }
  if (segmentFilter) {
    filtered = filtered.filter((r) => r.segment === segmentFilter);
  }

  const rows = filtered.map((r) => ({
    year: r.year,
    segment: r.segment,
    model: r.model,
    mape: r.mape,
    actual_usd: r.actual_usd,
    predicted_usd: r.predicted_usd,
    regime_label: r.regime_label || null,
  }));

  // Summary: per-model stats
  const summary: Record<string, any> = {};
  const models = [...new Set(nonSoft.map((r) => r.model))].sort();
  for (const m of models) {
    const mDf = nonSoft.filter((r) => r.model === m);
    const segMape: Record<string, number> = {};
    for (const seg of SEGMENTS) {
      const segRows = mDf.filter((r) => r.segment === seg);
      if (segRows.length > 0) {
        segMape[seg] = Math.round(segRows.reduce((s, r) => s + r.mape, 0) / segRows.length * 10) / 10;
      }
    }
    summary[m] = {
      mean_mape: Math.round(mDf.reduce((s, r) => s + r.mape, 0) / mDf.length * 10) / 10,
      n_folds: mDf.length,
      per_segment: segMape,
    };
  }

  // Data quality from anchors
  const anchors = anchorsData as any[];
  const dataQuality: Record<string, any> = {};
  for (const seg of SEGMENTS) {
    const segDf = anchors.filter((r) => r.segment === seg);
    const q4 = segDf.filter((r) => r.quarter === 4);
    const realQ4 = q4.filter((r) => r.n_sources > 0);
    const real = segDf.filter((r) => !r.estimated_flag);
    dataQuality[seg] = {
      real_points: real.length,
      interpolated_points: segDf.length - real.length,
      total_points: segDf.length,
      real_ratio: segDf.length > 0 ? Math.round(real.length / segDf.length * 100) / 100 : 0,
    };
  }

  // Model coverage
  const modelCoverage: Record<string, any> = {};
  for (const seg of SEGMENTS) {
    const segModels = [...new Set(nonSoft.filter((r) => r.segment === seg).map((r) => r.model))].sort();
    const hasEnsemble = segModels.some((m) => m.includes('ensemble'));
    modelCoverage[seg] = {
      models: segModels,
      has_ensemble: hasEnsemble,
      ensemble_note: hasEnsemble ? '' : 'Ensemble LOO not available for this segment',
    };
  }

  summary['_data_quality'] = dataQuality;
  summary['_model_coverage'] = modelCoverage;

  return NextResponse.json({
    data: rows,
    count: rows.length,
    summary,
    mape_matrix: buildMapeMatrix(nonSoft),
    ci_coverage: buildCiCoverage(nonSoft),
    regime_comparison: buildRegimeComparison(nonSoft),
    data_sources: buildDataSources(anchors),
  });
}
