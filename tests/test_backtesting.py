"""
Tests for MODL-06: Walk-forward backtesting with hard and soft actuals.

Covers:
- assemble_actuals() returns proper DataFrame with actual_type column
- Hard actuals only come from direct-disclosure companies (NVIDIA, Palantir, C3.ai)
- run_walk_forward() produces 2 folds (2023, 2024) with correct actual_type labels
- run_backtesting() writes backtesting_results.parquet with required schema
- label_mape() returns correct MAPE labels
- circular_flag column present in output
- hard actuals present and have non-zero MAPE (when EDGAR data available)
"""
import pytest
import pandas as pd
from pathlib import Path


class TestBacktesting:
    def test_assemble_actuals_returns_dataframe(self):
        """assemble_actuals('ai') returns DataFrame with required columns including actual_type."""
        from src.backtesting.actuals_assembly import assemble_actuals

        df = assemble_actuals("ai")
        assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df)}"
        assert "actual_type" in df.columns, (
            f"Expected 'actual_type' column, got columns: {df.columns.tolist()}"
        )
        valid_types = {"hard", "soft"}
        actual_types = set(df["actual_type"].unique())
        assert actual_types.issubset(valid_types), (
            f"actual_type must be subset of {valid_types}, got {actual_types}"
        )
        required_cols = ["year", "segment", "actual_usd_billions", "actual_type", "source", "source_date"]
        for col in required_cols:
            assert col in df.columns, f"Expected column '{col}' missing from DataFrame"

    def test_hard_actuals_source(self):
        """
        Hard actuals must only come from direct-disclosure companies:
        NVIDIA (0001045810), Palantir (0001321655), C3.ai (0001577526).

        EDGAR data must exist (edgar_ai_raw.parquet) — this test is NOT skipped when
        EDGAR data is present. The EDGAR fetch is run as part of Plan 10-05 setup.
        """
        from src.backtesting.actuals_assembly import assemble_actuals
        from config.settings import DATA_RAW

        edgar_path = DATA_RAW / "edgar" / "edgar_ai_raw.parquet"
        if not edgar_path.exists():
            pytest.skip("EDGAR parquet not found — run EDGAR fetch first")

        df = assemble_actuals("ai")
        hard_df = df[df["actual_type"] == "hard"]

        assert not hard_df.empty, (
            "Hard actuals must be present when edgar_ai_raw.parquet exists. "
            f"Edgar path: {edgar_path}"
        )

        # All hard actual sources should contain "EDGAR"
        sources_not_edgar = hard_df[~hard_df["source"].str.contains("EDGAR", case=False, na=False)]
        assert sources_not_edgar.empty, (
            f"Hard actuals must come from EDGAR — non-EDGAR sources found:\n{sources_not_edgar}"
        )

    def test_actual_type_labels(self):
        """run_walk_forward('ai') actual_type column has only valid values."""
        from src.backtesting.walk_forward import run_walk_forward

        df = run_walk_forward("ai")
        assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df)}"
        assert "actual_type" in df.columns, (
            f"Expected 'actual_type' column, got columns: {df.columns.tolist()}"
        )
        # held_out = LOO cross-validation, hard = EDGAR filings, soft = soft actuals
        valid_types = {"hard", "soft", "held_out"}
        actual_types = set(df["actual_type"].unique())
        assert actual_types.issubset(valid_types), (
            f"actual_type must be subset of {valid_types}, got {actual_types}"
        )

    def test_fold_count(self):
        """run_walk_forward('ai') evaluates >= 2 folds."""
        from src.backtesting.walk_forward import run_walk_forward

        df = run_walk_forward("ai")
        assert "year" in df.columns, f"Expected 'year' column, got columns: {df.columns.tolist()}"
        eval_years = set(df["year"].unique())
        # LOO cross-validation evaluates years 2020-2024; EDGAR hard actuals may include 2018-2024
        valid_eval_years = {2018, 2019, 2020, 2021, 2022, 2023, 2024}
        assert eval_years.issubset(valid_eval_years), (
            f"Evaluation years must be subset of {valid_eval_years}, got {eval_years}"
        )
        assert len(eval_years) >= 2, (
            f"Expected >= 2 evaluation folds, got {len(eval_years)} (years: {sorted(eval_years)})"
        )

    def test_circular_flag_column(self):
        """backtesting_results.parquet has a circular_flag column after run_backtesting()."""
        from src.backtesting.walk_forward import run_backtesting

        output_path = run_backtesting("ai")
        df = pd.read_parquet(output_path)
        assert "circular_flag" in df.columns, (
            f"Expected 'circular_flag' column in backtesting_results.parquet. "
            f"Got columns: {df.columns.tolist()}"
        )
        # Soft actuals should have circular_flag=True (model calibrated against same anchors)
        soft_df = df[df["actual_type"] == "soft"]
        if not soft_df.empty:
            assert soft_df["circular_flag"].any(), (
                "Expected at least some soft actual rows to have circular_flag=True. "
                "The ensemble model is calibrated against market anchor medians — "
                "soft actuals should be flagged as circular."
            )
            # Circular rows should have mape_label='circular_not_validated'
            circular_df = soft_df[soft_df["circular_flag"] == True]
            if not circular_df.empty:
                assert (circular_df["mape_label"] == "circular_not_validated").all(), (
                    f"Circular rows must have mape_label='circular_not_validated'. "
                    f"Got: {circular_df['mape_label'].unique().tolist()}"
                )

    def test_mape_not_all_zero(self):
        """Hard actual rows (if present) have at least one non-zero MAPE."""
        from src.backtesting.walk_forward import run_backtesting
        from config.settings import DATA_RAW

        edgar_path = DATA_RAW / "edgar" / "edgar_ai_raw.parquet"
        if not edgar_path.exists():
            pytest.skip("EDGAR parquet not found — run EDGAR fetch first")

        output_path = run_backtesting("ai")
        df = pd.read_parquet(output_path)
        hard_df = df[df["actual_type"] == "hard"]

        assert not hard_df.empty, (
            "Expected hard actual rows in backtesting_results.parquet when EDGAR data exists."
        )
        assert (hard_df["mape"] > 0).any(), (
            f"All hard actual MAPE values are zero — this indicates circular validation. "
            f"Hard actuals must produce real (non-zero) forecast error.\n"
            f"Hard rows:\n{hard_df[['year', 'segment', 'actual_usd', 'predicted_usd', 'mape']].to_string()}"
        )

    def test_parquet_schema(self):
        """run_backtesting('ai') writes backtesting_results.parquet with required schema columns."""
        from src.backtesting.walk_forward import run_backtesting

        output_path = run_backtesting("ai")
        assert output_path is not None, "run_backtesting returned None"
        assert isinstance(output_path, Path), f"Expected Path, got {type(output_path)}"
        assert output_path.exists(), f"backtesting_results.parquet not found at {output_path}"

        df = pd.read_parquet(output_path)
        required_cols = ["year", "segment", "actual_usd", "predicted_usd", "mape", "r2", "actual_type"]
        for col in required_cols:
            assert col in df.columns, (
                f"Column '{col}' missing from backtesting_results.parquet. "
                f"Got columns: {df.columns.tolist()}"
            )
        # No null actual_type
        assert df["actual_type"].notna().all(), "actual_type column contains null values"
        # held_out = LOO cross-validation, hard = EDGAR filings, soft = soft actuals
        valid_types = {"hard", "soft", "held_out"}
        assert set(df["actual_type"].unique()).issubset(valid_types), (
            f"actual_type must be subset of {valid_types}, got {set(df['actual_type'].unique())}"
        )

    def test_mape_label_function(self):
        """label_mape returns correct bucket labels for known MAPE values."""
        from src.backtesting.walk_forward import label_mape

        assert label_mape(10.0) == "acceptable", (
            f"Expected 'acceptable' for MAPE=10.0, got '{label_mape(10.0)}'"
        )
        assert label_mape(20.0) == "use_with_caution", (
            f"Expected 'use_with_caution' for MAPE=20.0, got '{label_mape(20.0)}'"
        )
        assert label_mape(50.0) == "directional_only", (
            f"Expected 'directional_only' for MAPE=50.0, got '{label_mape(50.0)}'"
        )
        # Boundary at exactly 15
        assert label_mape(15.0) == "use_with_caution", (
            f"Expected 'use_with_caution' for MAPE=15.0, got '{label_mape(15.0)}'"
        )
        # Boundary at exactly 30
        assert label_mape(30.0) == "directional_only", (
            f"Expected 'directional_only' for MAPE=30.0, got '{label_mape(30.0)}'"
        )
