"""
Dash application entry point and module-level data loading.

This module initializes the Dash app and pre-loads all data at startup. Data is read
once from Parquet files and stored as module globals (FORECASTS_DF, RESIDUALS_DF,
BACKTESTING_DF) for efficient reuse across callback invocations — Dash callbacks are
called on every user interaction, so data loading inside callbacks would create
unacceptable latency.

v1.1 update: point_estimate_real_2020 is USD billions directly (v1.1 models trained
on real USD market anchors). All tabs use native column names directly.

Normal/Expert mode content distinction:
- Normal mode: USD headlines, narrative insights, accessible language
- Expert mode: model diagnostics, CV metrics, ASSUMPTIONS.md refs
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path for config imports
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import numpy as np
import pandas as pd
import yaml
import dash
import dash_bootstrap_components as dbc
from config.settings import DATA_PROCESSED, MODELS_DIR

# Module-level data loading — read once at startup, filter in callbacks
FORECASTS_DF = pd.read_parquet(DATA_PROCESSED / "forecasts_ensemble.parquet")
RESIDUALS_DF = pd.read_parquet(DATA_PROCESSED / "residuals_statistical.parquet")
BACKTESTING_DF = pd.read_parquet(DATA_PROCESSED / "backtesting_results.parquet")
ANCHORS_DF = pd.read_parquet(DATA_PROCESSED / "market_anchors_ai.parquet")

with open(Path(__file__).resolve().parent.parent.parent / "config" / "industries" / "ai.yaml") as f:
    AI_CONFIG = yaml.safe_load(f)

SOURCE_ATTRIBUTION = AI_CONFIG["source_attribution"]
SEGMENTS = [seg["id"] for seg in AI_CONFIG["segments"]]
SEGMENT_DISPLAY = {seg["id"]: seg["display_name"] for seg in AI_CONFIG["segments"]}

# Compute diagnostics at startup from backtesting results
DIAGNOSTICS = {}
for segment, grp in BACKTESTING_DF.groupby("segment"):
    hard_rows = grp[grp["actual_type"] == "hard"]
    # Filter out -inf R² values (occur with single-sample folds)
    valid_r2 = hard_rows["r2"][hard_rows["r2"] > -1e10] if not hard_rows.empty else pd.Series(dtype=float)
    DIAGNOSTICS[segment] = {
        "mape": float(hard_rows["mape"].mean()) if not hard_rows.empty else None,
        "r2": float(valid_r2.mean()) if not valid_r2.empty else None,
        "mape_label": hard_rows["mape_label"].iloc[0] if not hard_rows.empty else "no_hard_actuals",
        "has_hard_actuals": not hard_rows.empty,
        "hard_details": [
            {"year": int(r["year"]), "mape": float(r["mape"]), "actual": float(r["actual_usd"]), "predicted": float(r["predicted_usd"])}
            for _, r in hard_rows.iterrows()
        ] if not hard_rows.empty else [],
    }

# Resolve the project root so assets/ is always served correctly regardless
# of which directory the app module lives in.
_assets_folder = str(Path(__file__).resolve().parent.parent.parent / "assets")

# Dash app instance
app = dash.Dash(
    __name__,
    assets_folder=_assets_folder,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "AI Industry Value Estimator"

# Import layout and callbacks AFTER app is created
from src.dashboard.layout import create_layout  # noqa: E402
import src.dashboard.callbacks  # noqa: F401, E402 — registers callbacks via decorator

app.layout = create_layout()
