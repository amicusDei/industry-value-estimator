"""
Statistical models subpackage — ARIMA, Prophet, and regression baselines.

Modules:
    arima: ARIMA(p,d,q) fitting, order selection via AICc, temporal CV
    prophet_model: Prophet with explicit 2022 GenAI changepoint, residual output
    regression: OLS with diagnostic-driven WLS/GLSAR upgrade; temporal CV scaffold

All models share the same temporal_cv_generic scaffold from regression.py,
ensuring consistent cross-validation methodology across model types.
Residuals are exported to data/processed/residuals_statistical.parquet for
Phase 3 ML training.
"""
