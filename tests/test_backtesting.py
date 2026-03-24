"""
Test scaffold for MODL-06: Walk-forward backtesting with hard and soft actuals.

All tests in this file are Wave 0 placeholders for Plan 10-04 implementation.
They document the behavioral contracts that Plan 10-04 must satisfy.

Test classes:
- TestBacktesting: documents backtesting_results.parquet schema and behavioral contracts
"""
import pytest


class TestBacktesting:
    @pytest.mark.skip(reason="Plan 10-04 implementation: assemble_actuals() hard actuals source")
    def test_hard_actuals_source(self):
        """
        Hard actuals must only come from companies with ai_disclosure_type 'direct'
        in ai.yaml: NVIDIA (0001045810), Palantir (0001321655), C3.ai (0001577552).
        Microsoft, Amazon, Alphabet (bundled disclosure) must NOT appear in hard actuals.

        Validates Pitfall 2: avoids circular validation (using attributed estimates
        as the actuals to validate those same attribution estimates).

        Expected: assemble_actuals() produces a DataFrame where
        actual_type == 'hard' rows have source_cik in {'0001045810', '0001321655', '0001577552'}.
        """
        pass

    @pytest.mark.skip(reason="Plan 10-04 implementation: actual_type column validation")
    def test_actual_type_labels(self):
        """
        backtesting_results.parquet must have an actual_type column with values
        'hard' or 'soft' only. No nulls, no other values.

        Hard actuals: EDGAR 10-K filed revenue (audited, direct-disclosure companies only).
        Soft actuals: market_anchors_ai.parquet analyst consensus estimates.

        Expected: df['actual_type'].isin(['hard', 'soft']).all() is True.
        """
        pass

    @pytest.mark.skip(reason="Plan 10-04 implementation: backtesting_results.parquet schema")
    def test_parquet_schema(self):
        """
        backtesting_results.parquet must contain these columns:
        year, segment, actual_usd, predicted_usd, residual_usd, model,
        holdout_type, actual_type, mape, r2.

        Expected: all schema columns present; no null actual_type values.
        """
        pass

    @pytest.mark.skip(reason="Plan 10-04 implementation: walk-forward fold count")
    def test_fold_count(self):
        """
        Walk-forward backtesting must produce exactly 3 evaluation folds:
        - Fold 1: train 2017-2021, evaluate 2022
        - Fold 2: train 2017-2022, evaluate 2023
        - Fold 3: train 2017-2023, evaluate 2024

        Expected: backtesting_results.parquet has 3 distinct evaluation years
        (2022, 2023, 2024) per segment.
        """
        pass
