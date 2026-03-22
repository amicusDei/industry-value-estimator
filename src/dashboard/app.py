"""
Dash application entry point and module-level data loading.

This module initializes the Dash app and pre-loads all data at startup. Data is read
once from Parquet files and stored as module globals (FORECASTS_DF, RESIDUALS_DF) for
efficient reuse across callback invocations — Dash callbacks are called on every user
interaction, so data loading inside callbacks would create unacceptable latency.

Value chain multiplier calibration is performed at module load time:
1. Reads anchor values from config/industries/ai.yaml (§ value_chain)
2. Derives per-segment multipliers: multiplier = anchor_usd_for_segment / index_at_anchor_year
3. Attaches USD columns (usd_point, usd_ci80_lower, etc.) to FORECASTS_DF
This calibration converts the dimensionless PCA composite index to USD billions for display.

Normal/Expert mode content distinction:
- Normal mode: USD headlines, narrative insights, accessible language
- Expert mode: raw composite index values, multiplier derivation tables, ASSUMPTIONS.md refs

See docs/ASSUMPTIONS.md section Value Chain Multiplier Calibration for the $200B 2023
anchor selection rationale and sensitivity analysis.
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

with open(Path(__file__).resolve().parent.parent.parent / "config" / "industries" / "ai.yaml") as f:
    AI_CONFIG = yaml.safe_load(f)

SOURCE_ATTRIBUTION = AI_CONFIG["source_attribution"]
SEGMENTS = [seg["id"] for seg in AI_CONFIG["segments"]]
SEGMENT_DISPLAY = {seg["id"]: seg["display_name"] for seg in AI_CONFIG["segments"]}

# ---------------------------------------------------------------------------
# Value chain multiplier — converts PCA composite index to USD billions
# Calibrated against industry consensus: ~$200B global AI market in 2023
# See config/industries/ai.yaml § value_chain and docs/ASSUMPTIONS.md
# ---------------------------------------------------------------------------
_vc = AI_CONFIG["value_chain"]
_anchor_year: int = int(_vc["anchor_year"])
_anchor_total_usd: float = float(_vc["anchor_value_usd_billions"])
_segment_shares: dict = _vc["segment_anchor_shares"]
_usd_floor: float = float(_vc.get("usd_floor_billions", 0.0))

# Compute per-segment multipliers:
#   anchor_usd_for_segment = anchor_total * segment_share
#   index_at_anchor = point_estimate_real_2020 for that segment at anchor_year
#   multiplier = anchor_usd / index_at_anchor (if index != 0)
# If index_at_anchor <= 0 (synthetic data artefact), fall back to global multiplier.
_df_anchor = FORECASTS_DF[FORECASTS_DF["year"] == _anchor_year]
_global_index_anchor = _df_anchor["point_estimate_real_2020"].sum()
_global_multiplier: float = (
    _anchor_total_usd / _global_index_anchor
    if _global_index_anchor != 0 else 1.0
)

VALUE_CHAIN_MULTIPLIERS: dict = {}  # segment -> USD-billions per index unit
for _seg in SEGMENTS:
    _seg_anchor_usd = _anchor_total_usd * _segment_shares.get(_seg, 0.25)
    _seg_rows = _df_anchor[_df_anchor["segment"] == _seg]
    _seg_idx_at_anchor = float(_seg_rows["point_estimate_real_2020"].iloc[0]) if len(_seg_rows) > 0 else 0.0
    if _seg_idx_at_anchor > 0:
        VALUE_CHAIN_MULTIPLIERS[_seg] = _seg_anchor_usd / _seg_idx_at_anchor
    else:
        # Fallback: global multiplier scaled by segment share
        VALUE_CHAIN_MULTIPLIERS[_seg] = _global_multiplier * _segment_shares.get(_seg, 0.25)

# Attach USD columns to FORECASTS_DF in-place
# usd_point, usd_ci80_lower, usd_ci80_upper, usd_ci95_lower, usd_ci95_upper
# Values are floored at usd_floor for display integrity
_usd_rows = []
for _seg, _grp in FORECASTS_DF.groupby("segment"):
    _mult = VALUE_CHAIN_MULTIPLIERS.get(_seg, _global_multiplier)
    _grp = _grp.copy()
    _grp["usd_point"] = (_grp["point_estimate_real_2020"] * _mult).clip(lower=_usd_floor)
    _grp["usd_ci80_lower"] = (_grp["ci80_lower"] * _mult).clip(lower=_usd_floor)
    _grp["usd_ci80_upper"] = (_grp["ci80_upper"] * _mult).clip(lower=_usd_floor)
    _grp["usd_ci95_lower"] = (_grp["ci95_lower"] * _mult).clip(lower=_usd_floor)
    _grp["usd_ci95_upper"] = (_grp["ci95_upper"] * _mult).clip(lower=_usd_floor)
    _usd_rows.append(_grp)
FORECASTS_DF = pd.concat(_usd_rows).sort_values(["segment", "year"]).reset_index(drop=True)

# Multiplier derivation string for Expert mode display
VALUE_CHAIN_DERIVATION: dict = {}
for _seg in SEGMENTS:
    _seg_anchor_usd = _anchor_total_usd * _segment_shares.get(_seg, 0.25)
    _seg_rows = _df_anchor[_df_anchor["segment"] == _seg]
    _seg_idx_at_anchor = float(_seg_rows["point_estimate_real_2020"].iloc[0]) if len(_seg_rows) > 0 else 0.0
    _mult = VALUE_CHAIN_MULTIPLIERS[_seg]
    VALUE_CHAIN_DERIVATION[_seg] = {
        "anchor_usd": _seg_anchor_usd,
        "index_at_anchor": _seg_idx_at_anchor,
        "multiplier": _mult,
        "method": "per_segment_anchor" if _seg_idx_at_anchor > 0 else "global_fallback",
    }

# Compute diagnostics at startup from residuals
DIAGNOSTICS = {}
for segment, grp in RESIDUALS_DF.groupby("segment"):
    residual = grp["residual"].to_numpy()
    DIAGNOSTICS[segment] = {
        "rmse": float(np.sqrt(np.mean(residual ** 2))),
        "mape": "N/A",  # Cannot compute — no actual values in residuals parquet
        "r2": "N/A",    # Cannot compute — no actual values in residuals parquet
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
