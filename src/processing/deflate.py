"""
Inflation adjustment module.

Deflates nominal monetary series to constant base-year USD using the
World Bank GDP deflator (NY.GDP.DEFL.ZS).

The GDP deflator from World Bank uses 2015=100 as its native base.
This module re-bases to 2020=100 internally by dividing all deflator
values by the 2020 observation.

Column naming convention:
- Input: columns with '_nominal_' in the name (e.g., gdp_nominal_2023)
- Output: renamed to '_real_{base_year}' (e.g., gdp_real_2020)
- Non-monetary columns: passed through unchanged

This module is the single enforcement point for the nominal/real distinction.
No nominal column should EVER reach data/processed/.
"""
import pandas as pd
from config.settings import BASE_YEAR


def deflate_to_base_year(
    nominal_series: pd.Series,
    deflator_series: pd.Series,
    base_year: int = BASE_YEAR,
    nominal_col_name: str = "",
) -> pd.Series:
    """
    Convert a nominal USD series to constant base_year USD.

    Formula: real_value = nominal_value * (deflator[base_year] / deflator[year])

    Parameters
    ----------
    nominal_series : pd.Series
        Values in current USD, indexed by year.
    deflator_series : pd.Series
        World Bank NY.GDP.DEFL.ZS index (2015=100 in raw API).
        Must share the same year index as nominal_series.
    base_year : int
        Target constant year (project standard: 2020).
    nominal_col_name : str
        Original column name — used only for error messages.

    Returns
    -------
    pd.Series
        Values in constant base_year USD.

    Raises
    ------
    ValueError
        If deflator is missing for the base year.
    """
    if base_year not in deflator_series.index:
        raise ValueError(
            f"Deflator missing for base year {base_year}. "
            f"Available years: {sorted(deflator_series.dropna().index.tolist())}. "
            f"Cannot deflate {nominal_col_name}."
        )
    base_deflator = deflator_series.loc[base_year]
    if pd.isna(base_deflator):
        raise ValueError(
            f"Deflator is NaN for base year {base_year}. "
            f"Cannot deflate {nominal_col_name}."
        )
    return nominal_series * (base_deflator / deflator_series)


def apply_deflation(
    df: pd.DataFrame,
    deflator_col: str = "gdp_deflator_index",
    base_year: int = BASE_YEAR,
) -> pd.DataFrame:
    """
    Apply deflation to all nominal columns in a DataFrame.

    Finds all columns containing '_nominal_' in their name,
    deflates them using the deflator column, and renames them
    to '_real_{base_year}'.

    Drops the original nominal columns. The deflator column is kept
    for audit purposes.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a deflator column and at least one '_nominal_' column.
        Index or column 'year' used to align with deflator.
    deflator_col : str
        Name of the column containing the GDP deflator index.
    base_year : int
        Target constant year (project standard: 2020).

    Returns
    -------
    pd.DataFrame
        With nominal columns replaced by real columns.

    Raises
    ------
    RuntimeError
        If the deflator column is missing.
    """
    if deflator_col not in df.columns:
        raise RuntimeError(
            f"GDP deflator column '{deflator_col}' missing from DataFrame. "
            f"Fetch NY.GDP.DEFL.ZS before running deflation. "
            f"Available columns: {list(df.columns)}"
        )

    result = df.copy()
    nominal_cols = [c for c in df.columns if "_nominal_" in c.lower()]

    if not nominal_cols:
        return result  # No nominal columns to deflate

    # Build a deflator series indexed by year for lookup
    if "year" in df.columns:
        deflator_by_year = df.set_index("year")[deflator_col]
    else:
        deflator_by_year = df[deflator_col]

    for col in nominal_cols:
        # Derive real column name: replace _nominal_ with _real_{base_year}
        # e.g., gdp_nominal_usd -> gdp_real_2020_usd
        # e.g., gdp_nominal_2023 -> gdp_real_2020
        real_col = col.replace("_nominal_", f"_real_{base_year}_").rstrip("_")

        # Build a deflator Series indexed by year for deflate_to_base_year.
        # deflate_to_base_year expects `base_year` to be a valid index value.
        # When year is a column, map row positions -> year values as the index.
        if "year" in df.columns:
            # Create a year-indexed series for lookup, then map back to row order
            year_to_deflator = deflator_by_year.to_dict()
            # Build deflator series with year as index (same as nominal_series)
            year_values = df["year"].values
            deflator_values = [year_to_deflator.get(y, float("nan")) for y in year_values]
            deflator_aligned = pd.Series(deflator_values, index=df["year"].values)
            nominal_aligned = pd.Series(df[col].values, index=df["year"].values)
        else:
            deflator_aligned = deflator_by_year
            nominal_aligned = df[col]

        result[real_col] = deflate_to_base_year(
            nominal_aligned,
            deflator_aligned,
            base_year=base_year,
            nominal_col_name=col,
        ).values  # .values to reset index back to DataFrame's positional index
        result = result.drop(columns=[col])

    return result
