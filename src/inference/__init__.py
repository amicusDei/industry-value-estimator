"""
Inference package — forecast assembly and model interpretability.

Modules:
    forecast: Assemble full forecast DataFrame with dual units (real 2020 USD + nominal)
              and monotonically clipped confidence interval bounds
    shap_analysis: SHAP TreeExplainer wrapper for LightGBM feature attribution

The inference layer is the final data transformation step before the dashboard.
It converts model outputs (per-segment arrays) into the forecasts_ensemble.parquet
schema consumed by src/dashboard/app.py.
"""
