"""CSV and Excel export endpoints."""

import io
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.data_loader import get_forecasts, get_companies

router = APIRouter(prefix="/api/v1", tags=["export"])


def _filter_forecasts(segment: str | None, valuation: str) -> "pd.DataFrame":
    import pandas as pd
    df = get_forecasts()
    if df.empty:
        return df

    if segment:
        df = df[df["segment"] == segment]

    # Select value columns based on valuation
    if valuation == "real_2020":
        rename_map = {
            "point_estimate_real_2020": "point_estimate",
            "ci80_lower": "ci80_lower",
            "ci80_upper": "ci80_upper",
            "ci95_lower": "ci95_lower",
            "ci95_upper": "ci95_upper",
        }
    else:
        rename_map = {
            "point_estimate_nominal": "point_estimate",
            "ci80_lower_nominal": "ci80_lower",
            "ci80_upper_nominal": "ci80_upper",
            "ci95_lower_nominal": "ci95_lower",
            "ci95_upper_nominal": "ci95_upper",
        }

    cols = ["year", "quarter", "segment", "is_forecast"]
    for src, dst in rename_map.items():
        if src in df.columns:
            df[dst] = df[src]
    cols += ["point_estimate", "ci80_lower", "ci80_upper", "ci95_lower", "ci95_upper"]

    return df[[c for c in cols if c in df.columns]]


@router.get("/export/csv")
def export_csv(
    segment: str | None = Query(None),
    valuation: str = Query("nominal"),
):
    df = _filter_forecasts(segment, valuation)
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    seg_label = segment or "all"
    filename = f"ai_forecasts_{seg_label}_{date.today().isoformat()}.csv"

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/excel")
def export_excel(
    segment: str | None = Query(None),
    valuation: str = Query("nominal"),
):
    import pandas as pd
    from openpyxl.styles import Font

    fc_df = _filter_forecasts(segment, valuation)
    co_df = get_companies()

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        fc_df.to_excel(writer, sheet_name="Forecasts", index=False)
        if not co_df.empty:
            co_df.to_excel(writer, sheet_name="Companies", index=False)

        # Methodology text sheet
        meth_df = pd.DataFrame({
            "Section": ["Source", "Model", "CIs", "Vintage"],
            "Description": [
                "8 analyst firms, scope-normalized median. EDGAR 10-K/10-Q for company attribution.",
                "ARIMA + Prophet + LightGBM ensemble, quarterly granularity.",
                "Bootstrap (1000 resamples), empirical percentiles. CI80 floor 25%, CI95 floor 40%.",
                f"Generated {date.today().isoformat()}",
            ],
        })
        meth_df.to_excel(writer, sheet_name="Methodology", index=False)

        # Bold headers + freeze panes
        for sheet_name in writer.sheets:
            ws = writer.sheets[sheet_name]
            for cell in ws[1]:
                cell.font = Font(bold=True)
            ws.freeze_panes = "A2"

    buf.seek(0)
    seg_label = segment or "all"
    filename = f"ai_forecasts_{seg_label}_{date.today().isoformat()}.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
