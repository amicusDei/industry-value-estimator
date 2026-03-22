"""
Diagnostics package — model evaluation metrics and structural break detection.

Modules:
    model_eval: RMSE, MAPE, R-squared, AIC/BIC/AICc, Ljung-Box test, model comparison
    structural_breaks: CUSUM test, Chow test, Markov switching regime detection

These tools are used in Phase 2 (statistical baseline) for:
1. Model selection between ARIMA and Prophet (compare_models)
2. Detecting the 2022 GenAI structural break (structural_breaks)
3. Deciding whether to upgrade OLS to WLS or GLSAR (via regression.py diagnostics)
"""
