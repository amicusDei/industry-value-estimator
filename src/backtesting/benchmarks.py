"""
Benchmark models for comparison against the ensemble forecaster.
Implements: naive (last-year growth), random walk, analyst consensus mean,
and Prophet-only (no LightGBM) baselines.
"""

import pandas as pd


def naive_forecast(y_series, n_steps=6):
    """Naive: assume last year's growth rate continues.
    y[t+1] = y[t] * (y[t] / y[t-1])"""
    last = float(y_series.iloc[-1])
    prev = float(y_series.iloc[-2]) if len(y_series) >= 2 else last
    growth = last / prev if prev > 0 else 1.0
    return [last * growth**(i+1) for i in range(n_steps)]


def random_walk_forecast(y_series, n_steps=6):
    """Random walk: y[t+1] = y[t] (no growth assumed)."""
    last = float(y_series.iloc[-1])
    return [last] * n_steps


def analyst_consensus_forecast(anchors_df, segment, n_steps=6):
    """Use analyst consensus growth rate from market_anchors.
    Compute historical CAGR from anchors and project forward."""
    seg = anchors_df[anchors_df['segment'] == segment].sort_values('estimate_year')
    if len(seg) < 2:
        return [float(seg.iloc[-1]['median_usd_billions_real_2020'])] * n_steps
    first_val = float(seg.iloc[0]['median_usd_billions_real_2020'])
    last_val = float(seg.iloc[-1]['median_usd_billions_real_2020'])
    n_years = int(seg.iloc[-1]['estimate_year'] - seg.iloc[0]['estimate_year'])
    if n_years > 0 and first_val > 0:
        cagr = (last_val / first_val) ** (1/n_years) - 1
    else:
        cagr = 0.0
    return [last_val * (1 + cagr)**(i+1) for i in range(n_steps)]
