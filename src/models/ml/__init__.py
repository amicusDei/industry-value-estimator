"""
ML models subpackage — LightGBM residual correction and quantile CI bounds.

Modules:
    gradient_boost: LightGBM point estimator trained on statistical residuals
    quantile_models: LightGBM quantile regressors for 80% and 95% CI bounds

The ML layer corrects systematic biases in the statistical baseline (Phase 2).
It does NOT replace the statistical forecast — it adds a residual correction term
(see ensemble.py for the additive blend formula). Features are lagged residuals
and a normalized year index, intentionally simple to avoid overfitting on ~15 obs.
"""
