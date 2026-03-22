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

with open(Path(__file__).resolve().parent.parent.parent / "config" / "industries" / "ai.yaml") as f:
    AI_CONFIG = yaml.safe_load(f)

SOURCE_ATTRIBUTION = AI_CONFIG["source_attribution"]
SEGMENTS = [seg["id"] for seg in AI_CONFIG["segments"]]
SEGMENT_DISPLAY = {seg["id"]: seg["display_name"] for seg in AI_CONFIG["segments"]}

# Compute diagnostics at startup from residuals
DIAGNOSTICS = {}
for segment, grp in RESIDUALS_DF.groupby("segment"):
    residual = grp["residual"].to_numpy()
    DIAGNOSTICS[segment] = {
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mape": "N/A",  # Cannot compute — no actual values in residuals parquet
        "r2": "N/A",    # Cannot compute — no actual values in residuals parquet
    }

# Dash app instance
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
app.title = "AI Industry Value Estimator"

# Import layout and callbacks AFTER app is created
from src.dashboard.layout import create_layout  # noqa: E402
import src.dashboard.callbacks  # noqa: F401, E402 — registers callbacks via decorator

app.layout = create_layout()
