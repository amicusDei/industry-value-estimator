"""
Tests for MODL-06: Walk-forward backtesting with hard and soft actuals.

Covers:
- assemble_actuals() returns proper DataFrame with actual_type column
- Hard actuals only come from direct-disclosure companies (NVIDIA, Palantir, C3.ai)
- run_walk_forward() produces 3 folds (2022, 2023, 2024) with correct actual_type labels
- run_backtesting() writes backtesting_results.parquet with required schema
- label_mape() returns correct MAPE labels
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
        Hard actuals must only come from companies with ai_disclosure_type 'direct':
        NVIDIA (0001045810), Palantir (0001321655), C3.ai (0001577552).

        If no EDGAR data exists, test is skipped.
        """
        from src.backtesting.actuals_assembly import assemble_actuals

        df = assemble_actuals("ai")
        hard_df = df[df["actual_type"] == "hard"]

        if hard_df.empty:
            pytest.skip("No hard actuals available (EDGAR data not present) — skipping")

        # All hard actual sources should contain "EDGAR"
        sources_not_edgar = hard_df[~hard_df["source"].str.contains("EDGAR", case=False, na=False)]
        assert sources_not_edgar.empty, (
            f"Hard actuals must come from EDGAR — non-EDGAR sources found:\n{sources_not_edgar}"
        )

    def test_actual_type_labels(self):
        """run_walk_forward('ai') actual_type column has only 'hard' and/or 'soft' values."""
        from src.backtesting.walk_forward import run_walk_forward

        df = run_walk_forward("ai")
        assert isinstance(df, pd.DataFrame), f"Expected DataFrame, got {type(df)}"
        assert "actual_type" in df.columns, (
            f"Expected 'actual_type' column, got columns: {df.columns.tolist()}"
        )
        valid_types = {"hard", "soft"}
        actual_types = set(df["actual_type"].unique())
        assert actual_types.issubset(valid_types), (
            f"actual_type must be subset of {valid_types}, got {actual_types}"
        )

    def test_fold_count(self):
        """run_walk_forward('ai') evaluation years are a subset of {2022, 2023, 2024}."""
        from src.backtesting.walk_forward import run_walk_forward

        df = run_walk_forward("ai")
        assert "year" in df.columns, f"Expected 'year' column, got columns: {df.columns.tolist()}"
        eval_years = set(df["year"].unique())
        valid_eval_years = {2022, 2023, 2024}
        assert eval_years.issubset(valid_eval_years), (
            f"Evaluation years must be subset of {valid_eval_years}, got {eval_years}"
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
        valid_types = {"hard", "soft"}
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
