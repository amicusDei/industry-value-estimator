# Phase 3: ML Ensemble and Validation - Research

**Researched:** 2026-03-22
**Domain:** LightGBM residual boosting, quantile regression confidence intervals, SHAP attribution, joblib serialization, ensemble weighting
**Confidence:** HIGH (all critical API details verified via official docs; stack already partially installed in project)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Ensemble weighting strategy**
- Method: Fixed weights from CV performance — weight each model proportional to its inverse CV error (e.g., if statistical RMSE=0.3 and LightGBM RMSE=0.2, LightGBM gets 60%)
- Scope: Per-segment weights primary (each segment gets its own blend ratio), global weights as fallback for segments with insufficient CV folds
- LightGBM features: Residuals only (pure residual learning) — LightGBM sees ONLY the statistical model residuals + lag features. True "residual boosting" — ML learns what statistics missed. Clean separation of responsibilities.
- Data vintage: Every output estimate tagged with the date of the latest data used (e.g., "AI market was $X trillion as of 2025-Q1 data"). Required by MODL-04. In DataFrame columns, not just metadata.

**Confidence interval calibration**
- Method: Quantile regression via LightGBM — train separate models for 10th/90th percentiles (80% CI) and 2.5th/97.5th percentiles (95% CI). Directly produces interval bounds.
- Fan shape: Claude calibrates based on data — let the quantile regression learn natural widening from CV folds. Don't force fan shapes if the data doesn't support it.
- No bare point forecasts: Every forecast output includes both point estimate and interval bounds (MODL-05).

**Output units**
- Primary: 2020 constant USD (trillions) — consistent with Phase 1 deflation base year
- Secondary: Reflated to nominal USD for headlines — "AI industry worth $X.X trillion (2020 USD) / $Y.Y trillion (nominal)"
- Both representations in the forecast output DataFrame

**Model serialization**
- Format: joblib (scikit-learn standard) — fast, handles LightGBM + sklearn pipelines natively
- Directory: `models/ai_industry/` (already exists on disk)
- Artifacts: Both serialized models AND pre-computed forecast DataFrames (point estimates + intervals). Dashboard loads forecasts directly without running inference. Cache invalidated when models are retrained.

**Pipeline runner**
- Script: `scripts/run_ensemble_pipeline.py` — single command: train LightGBM → build ensemble → forecast to 2030 → compute SHAP → serialize models → save forecasts
- Follows the pattern established by `scripts/run_statistical_pipeline.py` from Phase 2

### Claude's Discretion
- LightGBM hyperparameters (learning_rate, n_estimators, max_depth, etc.)
- Number of lag features derived from residuals
- SHAP analysis depth (summary plots vs force plots vs interaction effects)
- Exact quantile regression model configuration
- Model file naming convention within `models/ai_industry/`
- Deflation/reflation mechanics for nominal USD conversion
- Minimum CV folds threshold before falling back to global weights

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-02 | Build ML refinement model (LightGBM) trained on statistical model residuals | LightGBM scikit-learn API with `objective="regression"`, input from `residuals_statistical.parquet`. `temporal_cv_generic` reusable for CV. |
| MODL-03 | Create hybrid ensemble combining statistical and ML outputs with documented weighting | Per-segment inverse-RMSE weighting formula. `compare_models` in `model_eval.py` reusable for statistical vs. ensemble comparison. |
| MODL-04 | Generate market size point estimates with units and vintage date | Output DataFrame with `value_real_2020_trillions`, `value_nominal_trillions`, `data_vintage` columns. Vintage = max date of source data. |
| MODL-05 | Generate growth forecasts with calibrated confidence intervals (80%/95%) | LightGBM quantile regression (`objective="quantile"`, `alpha=0.1/0.9/0.025/0.975`). Four separate quantile models per segment. |
| MODL-07 | Compute SHAP values showing which variables (R&D spend, patent filings, VC investment) drive the forecast | `shap.TreeExplainer(lgbm_model)` + `shap.summary_plot()`. Feature names must match column names in feature matrix. |
</phase_requirements>

---

## Summary

Phase 3 builds on Phase 2's residuals parquet (`data/processed/residuals_statistical.parquet`, already on disk) to add the ML layer. The architecture is a three-model stack per segment: a point-estimate LightGBM regressor, two quantile regressors for 80% CI (alpha=0.10, alpha=0.90), and two for 95% CI (alpha=0.025, alpha=0.975). The ensemble combiner uses inverse-CV-RMSE weights per segment, with a global fallback for data-sparse segments.

The critical design constraint is pure residual learning: LightGBM trains only on the statistical model's residuals plus lag features derived from those residuals. This clean separation means the statistical layer handles trend/seasonality and LightGBM corrects the noise. Every output includes point estimate + both CI bounds + data vintage. Model artifacts are serialized via joblib; forecasts are pre-computed to parquet so the Phase 4 dashboard loads instantly without re-training.

The key infrastructure gap is that `lightgbm` and `shap` are not yet in `pyproject.toml`. Wave 0 of the plan must add them via `uv add`. All other dependencies (scikit-learn, pandas, pyarrow, joblib via sklearn) are already present.

**Primary recommendation:** Use `lightgbm.LGBMRegressor` with scikit-learn API throughout — point estimator (`objective="regression"`), quantile estimators (`objective="quantile"`, `alpha=q`). Feed `temporal_cv_generic` from Phase 2 directly. Use `shap.TreeExplainer` for SHAP. Serialize everything with `joblib.dump`.

---

## Standard Stack

### Core (already in pyproject.toml)
| Library | Version in project | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| scikit-learn | >=1.8.0 | `TimeSeriesSplit` for CV, `Pipeline` orchestration | Already established in Phases 1-2; `temporal_cv_generic` uses `TimeSeriesSplit` |
| pandas | >=3.0.1 | DataFrame manipulation, forecast output | Established project standard; CoW-safe patterns already in use |
| pyarrow | >=23.0.1 | Parquet I/O for forecast cache and residuals input | Already used for residuals output in Phase 2 |
| joblib | (via scikit-learn) | Model serialization | scikit-learn's own serialization tool; handles numpy arrays natively |

### Needs Adding to pyproject.toml
| Library | Recommended Version | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| lightgbm | >=4.6.0 | Point estimator + quantile regressors for residual learning | Fastest tabular gradient boosting; native sklearn API; handles small datasets (N~60 rows of residuals) without overfitting; supports `objective="quantile"` natively |
| shap | >=0.46.0 | SHAP values for feature attribution (MODL-07) | The standard for gradient boosting interpretability; `TreeExplainer` integrates directly with LightGBM's C++ backend for exact SHAP values |

**Installation:**
```bash
uv add lightgbm>=4.6.0 shap>=0.46.0
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LightGBM | XGBoost | XGBoost 3.2.0 is slightly more accurate on benchmarks but slower; no advantage at N~60 rows |
| LightGBM quantile | sklearn QuantileRegressor | Linear only; cannot capture nonlinear residual patterns |
| joblib | pickle | joblib is safer for numpy arrays and is sklearn's recommended format |
| shap.TreeExplainer | shap.Explainer (generic) | TreeExplainer is faster and exact for tree ensembles; generic Explainer falls back to sampling |

---

## Architecture Patterns

### Recommended Module Structure (new in Phase 3)
```
src/models/ml/
├── __init__.py
├── gradient_boost.py      # LightGBM point estimator + CV
└── quantile_models.py     # Four quantile regressors (80% + 95% CI)

src/models/
└── ensemble.py            # Per-segment weighting + combiner

src/inference/
├── __init__.py
├── forecast.py            # Load models, project 2025-2030, build output DataFrame
└── shap_analysis.py       # SHAP values + summary plots

scripts/
└── run_ensemble_pipeline.py  # Single-command runner (mirrors run_statistical_pipeline.py)
```

### Input Contract (from Phase 2)
```python
# data/processed/residuals_statistical.parquet
# Schema: year (int), segment (str), residual (float), model_type (str)
# Rows: ~60 (4 segments × 15 years: 2010-2024)
# Segments: ["ai_hardware", "ai_infrastructure", "ai_software", "ai_adoption"]
df = pd.read_parquet("data/processed/residuals_statistical.parquet")
```

### Output Contract (consumed by Phase 4 dashboard)
```python
# data/processed/forecasts_ensemble.parquet (pre-computed)
# Required columns:
#   year: int (2010-2030 inclusive, historical + forecast)
#   segment: str
#   point_estimate_real_2020: float  (2020 constant USD, trillions)
#   point_estimate_nominal: float    (nominal USD, trillions)
#   ci80_lower: float                (10th percentile, real 2020 USD)
#   ci80_upper: float                (90th percentile, real 2020 USD)
#   ci95_lower: float                (2.5th percentile, real 2020 USD)
#   ci95_upper: float                (97.5th percentile, real 2020 USD)
#   is_forecast: bool                (False for 2010-2024, True for 2025-2030)
#   data_vintage: str                (e.g. "2025-Q1", ISO format)
```

### Pattern 1: LightGBM Residual Learner

**What:** Train LightGBM on the statistical model's residuals. The model input is a feature matrix constructed from the residuals themselves (lags) plus the proxy indicators (R&D spend, patent filings, VC investment) for the SHAP requirement.

**When to use:** Always — this is the core ML layer.

**Feature engineering for the residual learner:**
```python
# src/models/ml/gradient_boost.py
# Source: LightGBM docs + project design decision (CONTEXT.md)

import pandas as pd
import numpy as np

def build_residual_features(residuals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature matrix for LightGBM from residuals parquet.

    Features per row:
    - residual_lag1: residual(t-1)
    - residual_lag2: residual(t-2)
    - year_norm: (year - 2010) / 14.0  — normalized time index
    - The feature names must exactly match proxy variable names from ai.yaml
      so SHAP output maps to "R&D spend", "patent filings", "VC investment"
    """
    df = residuals_df.sort_values(["segment", "year"]).copy()
    df["residual_lag1"] = df.groupby("segment")["residual"].shift(1)
    df["residual_lag2"] = df.groupby("segment")["residual"].shift(2)
    df["year_norm"] = (df["year"] - 2010) / 14.0
    return df.dropna()  # drop rows where lags are NaN (first 2 rows per segment)
```

**Point estimator training:**
```python
# Source: LightGBM official docs — LGBMRegressor sklearn API
import lightgbm as lgb

def fit_lgbm_point(X: np.ndarray, y: np.ndarray) -> lgb.LGBMRegressor:
    model = lgb.LGBMRegressor(
        objective="regression",
        n_estimators=100,        # conservative for N~50 rows after lag dropna
        max_depth=3,             # shallow trees prevent overfitting on small N
        learning_rate=0.05,
        num_leaves=7,            # 2^(max_depth) - 1 max; keep < 2^max_depth
        min_child_samples=3,     # min samples per leaf — critical for N~50
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1,              # suppress LightGBM output
    )
    model.fit(X, y)
    return model
```

### Pattern 2: Quantile Regression for Confidence Intervals

**What:** Train four separate LGBMRegressor instances, one per quantile bound. `objective="quantile"` + `alpha=q` directly minimizes the quantile loss for the given `q`.

**API verified:** LightGBM `objective="quantile"` with `alpha` parameter (verified via official LightGBM Parameters docs — alpha must be > 0.0, default 0.9).

**Sklearn API usage:**
```python
# Source: lightgbm.readthedocs.io/en/latest/Parameters.html — verified 2026-03-22

def fit_lgbm_quantile(X: np.ndarray, y: np.ndarray, alpha: float) -> lgb.LGBMRegressor:
    """
    alpha: 0.10 (CI80 lower), 0.90 (CI80 upper), 0.025 (CI95 lower), 0.975 (CI95 upper)
    """
    model = lgb.LGBMRegressor(
        objective="quantile",
        alpha=alpha,
        n_estimators=100,
        max_depth=3,
        learning_rate=0.05,
        num_leaves=7,
        min_child_samples=3,
        subsample=0.8,
        random_state=42,
        verbose=-1,
    )
    model.fit(X, y)
    return model

# Four models per segment:
QUANTILE_MODELS = {
    "ci80_lower": 0.10,
    "ci80_upper": 0.90,
    "ci95_lower": 0.025,
    "ci95_upper": 0.975,
}
```

**Note on CI crossing:** Quantile models trained independently can produce crossing intervals (ci80_lower > ci80_upper) on extrapolation. Apply monotonic clipping in the forecast step: `ci95_lower <= ci80_lower <= point <= ci80_upper <= ci95_upper`.

### Pattern 3: Per-Segment Inverse-RMSE Ensemble Weighting

**What:** Compute CV RMSE for statistical model and LightGBM model separately, then weight by inverse RMSE.

**Formula:**
```python
# src/models/ensemble.py
# Source: CONTEXT.md locked decision — inverse CV error weighting

def compute_ensemble_weights(
    stat_cv_rmse: float,
    lgbm_cv_rmse: float
) -> tuple[float, float]:
    """
    Returns (stat_weight, lgbm_weight) summing to 1.0.

    Example: stat_rmse=0.3, lgbm_rmse=0.2
    → inv_stat = 1/0.3 = 3.33, inv_lgbm = 1/0.2 = 5.0
    → total = 8.33
    → stat_weight = 3.33/8.33 = 0.40, lgbm_weight = 5.0/8.33 = 0.60
    """
    inv_stat = 1.0 / (stat_cv_rmse + 1e-10)
    inv_lgbm = 1.0 / (lgbm_cv_rmse + 1e-10)
    total = inv_stat + inv_lgbm
    return float(inv_stat / total), float(inv_lgbm / total)


def blend_forecasts(
    stat_pred: np.ndarray,
    lgbm_correction: np.ndarray,
    stat_weight: float,
    lgbm_weight: float,
) -> np.ndarray:
    """
    Ensemble: stat_pred is the statistical baseline forecast.
    lgbm_correction is LightGBM's predicted residual correction.
    Final forecast = stat_pred + lgbm_weight * lgbm_correction

    Note: LightGBM was trained on residuals, so its output IS a correction,
    not an independent forecast. The blend is additive not convex.
    """
    return stat_pred + lgbm_weight * lgbm_correction
```

**Important subtlety:** Because LightGBM is trained on residuals (not on the target directly), the ensemble combination is additive (stat_pred + weight * residual_correction), not a convex blend of two independent forecasts. The weight controls how much of the ML's residual correction to apply.

### Pattern 4: SHAP Attribution

**What:** Use `shap.TreeExplainer` for exact SHAP values on the LightGBM point estimator. Generates feature importance showing which proxy variables drive the forecast.

```python
# src/inference/shap_analysis.py
# Source: shap.readthedocs.io — TreeExplainer verified 2026-03-22

import shap
import lightgbm as lgb
import numpy as np

def compute_shap_values(
    model: lgb.LGBMRegressor,
    X: np.ndarray,
    feature_names: list[str],
) -> dict:
    """
    Returns dict with:
    - shap_values: np.ndarray shape (n_samples, n_features)
    - expected_value: float (base value)
    - feature_names: list[str]
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    return {
        "shap_values": shap_values,
        "expected_value": float(explainer.expected_value),
        "feature_names": feature_names,
    }


def save_shap_summary_plot(shap_dict: dict, X: np.ndarray, output_path: str) -> None:
    """Save SHAP summary plot to file (PNG). Used in Phase 4 dashboard and Phase 5 paper."""
    import matplotlib.pyplot as plt
    shap.summary_plot(
        shap_dict["shap_values"],
        X,
        feature_names=shap_dict["feature_names"],
        show=False,
    )
    plt.savefig(output_path, bbox_inches="tight", dpi=150)
    plt.close()
```

**Feature names must match proxy variable IDs from `ai.yaml`**: `rd_ict_pct_gdp`, `ai_patent_filings`, `vc_ai_investment`. These are the "R&D spend", "patent filings", "VC investment" variables referenced in MODL-07. Include them in the feature matrix by joining with processed data, or use the lag features with descriptive names if proxy data is not yet populated.

### Pattern 5: Model Serialization

**What:** Use `joblib.dump` / `joblib.load` to serialize models. Store both trained model objects and pre-computed forecast DataFrames.

```python
# Source: scikit-learn docs — joblib serialization (joblib is sklearn's dependency)
import joblib
from pathlib import Path

MODELS_DIR = Path("models/ai_industry")

def save_models(segment: str, models: dict) -> None:
    """
    models dict keys: "point", "ci80_lower", "ci80_upper", "ci95_lower", "ci95_upper"
    File naming: models/ai_industry/{segment}_lgbm_{key}.joblib
    """
    for key, model in models.items():
        path = MODELS_DIR / f"{segment}_lgbm_{key}.joblib"
        joblib.dump(model, path)


def load_models(segment: str) -> dict:
    models = {}
    for key in ["point", "ci80_lower", "ci80_upper", "ci95_lower", "ci95_upper"]:
        path = MODELS_DIR / f"{segment}_lgbm_{key}.joblib"
        models[key] = joblib.load(path)
    return models
```

**Also serialize ensemble weights:**
```python
# models/ai_industry/ensemble_weights.joblib
# dict: {segment: {"stat_weight": float, "lgbm_weight": float}}
```

### Pattern 6: Data Vintage Tagging (MODL-04)

**What:** Every row in the forecast DataFrame must carry a `data_vintage` column indicating the latest data used.

```python
# Vintage = max year in residuals_statistical.parquet + quarter estimate
# Since synthetic data runs 2010-2024, vintage = "2024-Q4"
# When live API data is used, compute from max(year) column

def get_data_vintage(residuals_df: pd.DataFrame) -> str:
    """Returns 'YYYY-QN' string from max year in residuals."""
    max_year = int(residuals_df["year"].max())
    return f"{max_year}-Q4"  # annual data, assume Q4
```

### Anti-Patterns to Avoid

- **Training on target directly:** LightGBM must train on residuals only. Training on the raw segment values defeats the two-stage hybrid design and loses the methodology paper story.
- **Training quantile models on different features than point estimator:** Use the same feature matrix for all five models per segment. Inconsistent features make the CI bounds incoherent.
- **Storing only model files, not forecast DataFrames:** The dashboard loads `forecasts_ensemble.parquet` directly. If only model files are stored, Phase 4 must re-run inference at every dashboard start — violates the architecture (ARCHITECTURE.md Anti-Pattern 2).
- **Bare point forecasts as output:** Every forecast output must include CI bounds. Never expose a column with only point estimates and no intervals (MODL-05).
- **Crossing CI bounds without clipping:** Quantile models trained independently can cross under distribution shift. Always enforce `ci95_lower <= ci80_lower <= point <= ci80_upper <= ci95_upper` via monotonic clipping before saving.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Gradient boosting | Custom gradient descent loop | `lightgbm.LGBMRegressor` | LightGBM handles histogram binning, leaf-wise growth, regularization, missing values natively |
| Quantile loss | Custom quantile pinball loss function | `LGBMRegressor(objective="quantile", alpha=q)` | LightGBM implements quantile loss natively with alpha parameter; verified in official docs |
| SHAP values | Manual Shapley calculation | `shap.TreeExplainer` | Exact Tree SHAP is O(TLD²) — manually computing for tree ensembles is infeasible |
| Model serialization | Custom pickle wrapper | `joblib.dump` / `joblib.load` | joblib handles numpy arrays, large objects, and compression automatically |
| Cross-validation | Custom fold loop | `temporal_cv_generic` from `regression.py` | Already implemented and tested in Phase 2; accepts any fit_fn/forecast_fn callable |
| Model comparison | Custom metrics | `compare_models` + `compute_rmse` from `model_eval.py` | Already implemented and tested; produces structured comparison dicts |

**Key insight:** The entire CV infrastructure from Phase 2 (`temporal_cv_generic`, `compute_rmse`, `compute_mape`, `compare_models`) is directly reusable for LightGBM. The callable-based design of `temporal_cv_generic` was explicitly built for this reuse.

---

## Common Pitfalls

### Pitfall 1: Overfitting on N~50 Residual Rows
**What goes wrong:** LightGBM with default hyperparameters (100+ leaves, deep trees) memorizes the 50 residual rows perfectly. CV RMSE is near zero but out-of-sample forecasts diverge wildly.
**Why it happens:** Default LightGBM parameters are tuned for thousands of rows, not 50.
**How to avoid:** Set `max_depth=3`, `num_leaves=7`, `min_child_samples=3`, `n_estimators=100`. These constrain tree complexity to match the data volume. CV will naturally select away from overfitting if splits are large enough.
**Warning signs:** Training RMSE < 0.001 with CV RMSE >> training RMSE; forecasts outside historical range by >5x.

### Pitfall 2: Lag Features Creating NaN-Induced Segment Imbalance
**What goes wrong:** Adding 2 lags drops the first 2 rows per segment. With 15 rows per segment, 2 lags leaves 13 rows — but `dropna()` must be applied after groupby-shift, not before, or you corrupt cross-segment rows.
**Why it happens:** Pandas `groupby().shift()` inserts NaN only for the first rows of each group, but a naive `dropna()` can drop rows from other groups that happened to have NaN values for unrelated reasons.
**How to avoid:** Apply `dropna(subset=["residual_lag1", "residual_lag2"])` specifically on the lag columns only.

### Pitfall 3: Quantile Crossing on Extrapolation
**What goes wrong:** For the 2025-2030 forecast horizon (unseen during training), quantile models produce `ci80_lower > ci80_upper` or `point_estimate < ci95_lower`.
**Why it happens:** Each quantile model is independently trained; they are not jointly constrained to preserve ordering.
**How to avoid:** After generating all five forecasts per segment per year, apply monotonic correction:
```python
# Enforce CI ordering in post-processing
row["ci95_lower"] = min(row["ci95_lower"], row["ci80_lower"], row["point"])
row["ci80_lower"] = min(row["ci80_lower"], row["point"])
row["ci80_upper"] = max(row["ci80_upper"], row["point"])
row["ci95_upper"] = max(row["ci95_upper"], row["ci80_upper"])
```
**Warning signs:** Any row where `ci80_lower >= ci80_upper` in the forecast DataFrame.

### Pitfall 4: SHAP Feature Names Not Matching DataFrame Columns
**What goes wrong:** `shap.summary_plot` shows feature names as "Feature 0", "Feature 1" instead of "rd_ict_pct_gdp", "ai_patent_filings".
**Why it happens:** When `X` is passed as a numpy array (not DataFrame), SHAP falls back to positional names.
**How to avoid:** Pass `X` as a `pd.DataFrame` with correctly named columns to `explainer.shap_values(X)`, or pass `feature_names` explicitly to `shap.summary_plot`.

### Pitfall 5: Vintage Column as Metadata Only (Violates MODL-04)
**What goes wrong:** Vintage date stored only in Parquet file metadata (schema.metadata), not as a column. Phase 4 dashboard cannot access it per-row.
**Why it happens:** CONTEXT.md explicitly requires "In DataFrame columns, not just metadata."
**How to avoid:** Include `data_vintage: str` as a proper column in the forecast DataFrame — every row has the vintage string.

### Pitfall 6: Missing `__init__.py` in New Module Directories
**What goes wrong:** `from src.models.ml.gradient_boost import fit_lgbm_point` raises `ModuleNotFoundError`.
**Why it happens:** `src/models/ml/` and `src/inference/` are new directories not yet created.
**How to avoid:** Wave 0 creates `src/models/ml/__init__.py` and `src/inference/__init__.py` as empty files.

### Pitfall 7: sys.path Not Injected in Pipeline Script
**What goes wrong:** `uv run python scripts/run_ensemble_pipeline.py` fails with `ModuleNotFoundError: No module named 'src'`.
**Why it happens:** Script-level imports need the project root on sys.path.
**How to avoid:** Copy the sys.path injection pattern from `run_statistical_pipeline.py` (lines 36-38):
```python
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
```

---

## Code Examples

Verified patterns from official sources and existing project code:

### LightGBM Quantile Regression (verified: lightgbm.readthedocs.io/en/latest/Parameters.html)
```python
import lightgbm as lgb

# 80% CI lower bound (10th percentile)
q10_model = lgb.LGBMRegressor(
    objective="quantile",
    alpha=0.10,          # alpha is the quantile level; must be > 0.0
    n_estimators=100,
    max_depth=3,
    verbose=-1,
)
q10_model.fit(X_train, y_train)
lower_bound = q10_model.predict(X_forecast)

# 95% CI upper bound (97.5th percentile)
q975_model = lgb.LGBMRegressor(
    objective="quantile",
    alpha=0.975,
    n_estimators=100,
    max_depth=3,
    verbose=-1,
)
q975_model.fit(X_train, y_train)
upper_bound = q975_model.predict(X_forecast)
```

### SHAP TreeExplainer with LightGBM (verified: shap.readthedocs.io)
```python
import shap
import pandas as pd

# X_train must be a DataFrame for named features in summary plot
explainer = shap.TreeExplainer(lgbm_point_model)
shap_values = explainer.shap_values(X_train_df)  # shape: (n_samples, n_features)

# Summary plot — shows which features push forecast up/down across all segments
shap.summary_plot(shap_values, X_train_df, show=False)
import matplotlib.pyplot as plt
plt.savefig("models/ai_industry/shap_summary.png", bbox_inches="tight", dpi=150)
plt.close()
```

### Reusing temporal_cv_generic from Phase 2
```python
# src/models/statistical/regression.py — temporal_cv_generic is already callable-based
from src.models.statistical.regression import temporal_cv_generic
import lightgbm as lgb
import numpy as np

def lgbm_cv_for_segment(y_residuals: np.ndarray, X_features: np.ndarray) -> list[dict]:
    """Wrap LightGBM fit/predict in temporal_cv_generic callable signatures."""

    def fit_fn(train_y):
        # temporal_cv_generic passes only the series slice — need X aligned
        # Use a wrapper that reconstructs X from the training index
        train_idx = slice(0, len(train_y))  # temporal_cv_generic uses slices
        model = lgb.LGBMRegressor(objective="regression", max_depth=3, verbose=-1)
        model.fit(X_features[train_idx], train_y)
        return model

    def forecast_fn(model, steps):
        # Must provide future X features for LightGBM prediction
        # For residual learning, use zeros as a conservative fallback
        # (or extrapolate lag features from last known residuals)
        future_X = np.zeros((steps, X_features.shape[1]))
        return model.predict(future_X)

    return temporal_cv_generic(y_residuals, fit_fn, forecast_fn, n_splits=3)
```

**Note:** `temporal_cv_generic`'s callable interface was designed to be model-agnostic, but it passes only the `y` series slice to `fit_fn` and `steps` to `forecast_fn`. For LightGBM with feature matrices, a thin wrapper that manages X alignment is needed. Keep the wrapper simple — the CV infrastructure itself does not need modification.

### joblib Serialization (sklearn standard)
```python
import joblib
from pathlib import Path

# Save
joblib.dump(lgbm_point_model, Path("models/ai_industry/ai_software_lgbm_point.joblib"))

# Load (by Phase 4 inference engine)
model = joblib.load(Path("models/ai_industry/ai_software_lgbm_point.joblib"))
predictions = model.predict(X_new)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual pickle for sklearn | joblib.dump (sklearn standard) | ~2015 | joblib handles large arrays and compression; pickle has security issues with untrusted files |
| SHAP kernel explainer (slow, approximate) | TreeExplainer (exact, fast) | SHAP v0.28 (2019) | Orders of magnitude faster for tree models; exact values not approximate |
| XGBoost as default gradient booster | LightGBM for small-N tabular | 2017+ | LightGBM trains 5-10x faster and uses less memory; equivalent accuracy at N~60 |
| pandas apply() loops for lag features | groupby().shift() | pandas 1.x | CoW-safe shift is the idiomatic pandas 3.0 pattern |

**Not deprecated, but project-specific note:**
- `shap.summary_plot()` remains the standard (not deprecated), but newer SHAP releases also offer `shap.plots.beeswarm()` as an alternative. Either is acceptable; `summary_plot` is more widely documented.

---

## Open Questions

1. **Proxy features in SHAP (MODL-07)**
   - What we know: MODL-07 requires SHAP to show "R&D spend, patent filings, VC investment" driving the forecast. The feature names in `ai.yaml` are `rd_ict_pct_gdp`, `ai_patent_filings`, `vc_ai_investment`.
   - What's unclear: Phase 3 uses synthetic residuals (the processed proxy data hasn't been joined into the residuals parquet yet). The residual features are lags of residuals + year_norm, not the actual proxy variables.
   - Recommendation: For Phase 3 with synthetic data, include year-normalized proxy proxies as placeholder columns in the feature matrix (even if constant or random) so the SHAP infrastructure is built and tested. When live API data is available, the features will be real. Document this limitation in ASSUMPTIONS.md. Alternatively, add the proxy column names to the feature matrix using the same synthetic data generation approach from `run_statistical_pipeline.py`.

2. **Minimum CV folds threshold for global weight fallback**
   - What we know: Per-segment weights are primary; global weights are the fallback for segments with insufficient CV folds. `temporal_cv_generic` uses `TimeSeriesSplit(n_splits=3)` — with N=13 rows per segment (after 2-lag dropna), 3 folds gives train sizes of ~4/6/8 rows.
   - What's unclear: At what CV fold count does per-segment weighting become unreliable? With N=13, 3 folds is borderline.
   - Recommendation: Use n_splits=3 as the minimum. If any fold produces RMSE=NaN or RMSE>10x the mean of other folds (indicating a degenerate fold), fall back to global weights computed from all segments pooled. Claude can determine the exact threshold during implementation.

3. **Reflation (nominal USD) mechanics**
   - What we know: CONTEXT.md requires both real 2020 USD and nominal USD in the output DataFrame. The `BASE_YEAR=2020` and GDP deflator indicator `NY.GDP.DEFL.ZS` are defined in `config/settings.py`.
   - What's unclear: For the 2025-2030 forecast horizon, nominal reflation requires projected deflator values (actual deflator only exists through 2024). A common approach is to use historical CAGR of the deflator (typically 2-3%) applied as a constant forward projection.
   - Recommendation: Compute reflation factor as `(deflator_year / deflator_2020)` using historical data through 2024, then extrapolate deflator at its trailing 5-year CAGR for 2025-2030. Claude can implement this in the forecast engine.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ |
| Config file | pyproject.toml (no pytest.ini — pytest auto-discovers) |
| Quick run command | `uv run pytest tests/test_ml_models.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-02 | LightGBM trains on residuals and reduces CV RMSE vs. statistical baseline | unit | `uv run pytest tests/test_ml_models.py::TestLGBMResidualLearner -x -q` | ❌ Wave 0 |
| MODL-02 | Feature matrix construction from residuals parquet (lags, year_norm) | unit | `uv run pytest tests/test_ml_models.py::TestFeatureEngineering -x -q` | ❌ Wave 0 |
| MODL-03 | Ensemble weights sum to 1.0; per-segment weights differ from global | unit | `uv run pytest tests/test_ensemble.py::TestEnsembleWeights -x -q` | ❌ Wave 0 |
| MODL-03 | Ensemble combiner produces forecast within plausible range | unit | `uv run pytest tests/test_ensemble.py::TestEnsembleCombiner -x -q` | ❌ Wave 0 |
| MODL-04 | Forecast DataFrame has data_vintage column (str, not metadata) | unit | `uv run pytest tests/test_forecast_output.py::test_vintage_column -x -q` | ❌ Wave 0 |
| MODL-04 | Forecast DataFrame has both real_2020 and nominal USD columns | unit | `uv run pytest tests/test_forecast_output.py::test_output_units -x -q` | ❌ Wave 0 |
| MODL-05 | Every forecast row has ci80_lower, ci80_upper, ci95_lower, ci95_upper | unit | `uv run pytest tests/test_forecast_output.py::test_no_bare_point_forecasts -x -q` | ❌ Wave 0 |
| MODL-05 | CI bounds are monotonically ordered (ci95_lower <= ci80_lower <= point <= ci80_upper <= ci95_upper) | unit | `uv run pytest tests/test_forecast_output.py::test_ci_ordering -x -q` | ❌ Wave 0 |
| MODL-07 | SHAP values shape matches (n_samples, n_features); feature names present | unit | `uv run pytest tests/test_shap.py::TestSHAPValues -x -q` | ❌ Wave 0 |
| MODL-07 | SHAP summary plot saves to file without error | unit | `uv run pytest tests/test_shap.py::test_summary_plot_saves -x -q` | ❌ Wave 0 |
| (all) | Serialized models load and produce predictions without re-training | unit | `uv run pytest tests/test_serialization.py -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_ml_models.py tests/test_ensemble.py tests/test_forecast_output.py tests/test_shap.py tests/test_serialization.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ml_models.py` — covers MODL-02 (LightGBM fitting, feature engineering, CV)
- [ ] `tests/test_ensemble.py` — covers MODL-03 (weighting, combining)
- [ ] `tests/test_forecast_output.py` — covers MODL-04, MODL-05 (output schema, vintage, CI)
- [ ] `tests/test_shap.py` — covers MODL-07 (SHAP values, summary plot)
- [ ] `tests/test_serialization.py` — covers artifact save/load round-trip
- [ ] `src/models/ml/__init__.py` — new directory, needs empty `__init__.py`
- [ ] `src/inference/__init__.py` — new directory, needs empty `__init__.py`
- [ ] Package additions: `uv add lightgbm>=4.6.0 shap>=0.46.0`

---

## Sources

### Primary (HIGH confidence)
- LightGBM Parameters docs (lightgbm.readthedocs.io/en/latest/Parameters.html) — `objective="quantile"`, `alpha` parameter semantics verified 2026-03-22
- SHAP docs (shap.readthedocs.io) — `TreeExplainer`, `shap_values()`, `summary_plot()` API verified 2026-03-22
- Project source code (`src/models/statistical/regression.py`) — `temporal_cv_generic` callable interface confirmed directly readable
- Project source code (`src/models/statistical/prophet_model.py`) — `save_all_residuals` Parquet schema confirmed; residuals parquet at `data/processed/residuals_statistical.parquet` confirmed on disk
- `pyproject.toml` — package versions and what's missing (lightgbm, shap not yet added)
- `config/settings.py` — `MODELS_DIR`, `DATA_PROCESSED`, `BASE_YEAR` constants confirmed

### Secondary (MEDIUM confidence)
- SHAP Census/LightGBM notebook (shap.readthedocs.io) — `shap.TreeExplainer(lgbm_model)` + `shap.summary_plot()` pattern confirmed
- LightGBM Python API docs (LGBMRegressor) — sklearn-compatible interface confirmed; quantile params referenced to Parameters.html
- Existing Phase 2 patterns (CONTEXT.md canonical refs) — reuse contracts for `temporal_cv_generic`, `compare_models`, `compute_rmse` confirmed by reading source

### Tertiary (LOW confidence)
- None — all critical claims verified via official sources or project source code

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versions verified in pyproject.toml; LightGBM and SHAP APIs verified via official docs
- Architecture: HIGH — directly derived from project's own CONTEXT.md locked decisions and existing Phase 2 code contracts
- Pitfalls: HIGH — derived from project-specific constraints (N~50 rows, quantile crossing, SHAP naming) with verified technical basis
- Test map: HIGH — follows existing project TDD pattern from Phases 1-2; test files are new but framework and commands are established

**Research date:** 2026-03-22
**Valid until:** 2026-06-22 (LightGBM and SHAP APIs are stable; 90-day horizon)
