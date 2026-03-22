"""
Models package — statistical baseline and ML correction layers.

Subpackages:
    statistical: ARIMA, Prophet, and OLS/WLS/GLSAR regression models
    ml: LightGBM point estimator and quantile regression for CI bounds

Module:
    ensemble: Inverse-RMSE weighting and additive blend (stat + ML correction)

Design:
    Phase 2 (statistical) provides the baseline trend forecast per segment.
    Phase 3 (ML) learns systematic residuals from the statistical models and
    adds a residual correction term. The ensemble.py module combines them via
    an additive blend weighted by inverse cross-validation RMSE.
"""
