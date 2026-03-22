"""
SHAP TreeExplainer wrapper and summary plot saver for LightGBM models.

Computes SHAP feature attribution values using TreeExplainer and saves
beeswarm summary plots to PNG for model interpretability reports.

Exports:
- compute_shap_values: run TreeExplainer on a fitted LGBMRegressor
- save_shap_summary_plot: save SHAP beeswarm summary plot to PNG file
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
import shap


def compute_shap_values(
    model: lgb.LGBMRegressor,
    X: "np.ndarray | pd.DataFrame",
    feature_names: list[str],
) -> dict:
    """
    Compute SHAP values for a fitted LightGBM model using TreeExplainer.

    Parameters
    ----------
    model : lgb.LGBMRegressor
        A fitted LightGBM regression model.
    X : np.ndarray or pd.DataFrame
        Feature matrix, shape (n_samples, n_features).
    feature_names : list[str]
        Names of input features (used for plotting and attribution tables).

    Returns
    -------
    dict
        {
            "shap_values": np.ndarray of shape (n_samples, n_features),
            "expected_value": float (model baseline, SHAP E[f(x)]),
            "feature_names": list[str] (same as input feature_names),
        }
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return {
        "shap_values": shap_values,
        "expected_value": float(explainer.expected_value),
        "feature_names": feature_names,
    }


def save_shap_summary_plot(
    shap_dict: dict,
    X: "np.ndarray | pd.DataFrame",
    output_path: "str | Path",
) -> None:
    """
    Save a SHAP beeswarm summary plot to a PNG file.

    Uses the non-interactive Agg matplotlib backend for headless execution
    (CI/CD, server environments without a display).

    Parameters
    ----------
    shap_dict : dict
        Output of compute_shap_values: must contain "shap_values" (np.ndarray)
        and "feature_names" (list[str]).
    X : np.ndarray or pd.DataFrame
        Feature matrix used to compute SHAP values (for color gradient).
    output_path : str or Path
        Destination path for the PNG file. Parent directory must exist.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    shap.summary_plot(
        shap_dict["shap_values"],
        X,
        feature_names=shap_dict["feature_names"],
        show=False,
    )
    plt.savefig(str(output_path), bbox_inches="tight", dpi=150)
    plt.close()
