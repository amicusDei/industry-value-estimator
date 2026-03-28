"""Company attribution endpoints."""

from fastapi import APIRouter

from api.data_loader import get_companies
from api.schemas import CompaniesResponse, CompanyRow

router = APIRouter(prefix="/api/v1", tags=["companies"])


@router.get("/companies", response_model=CompaniesResponse)
def list_companies():
    df = get_companies()
    if df.empty:
        return CompaniesResponse(data=[], count=0)

    rows = [
        CompanyRow(
            company_name=str(r["company_name"]),
            cik=str(r["cik"]),
            segment=str(r["segment"]),
            ai_revenue_usd_billions=float(r["ai_revenue_usd_billions"]),
            attribution_method=str(r["attribution_method"]),
            value_chain_layer=str(r["value_chain_layer"]),
        )
        for _, r in df.iterrows()
    ]

    return CompaniesResponse(data=rows, count=len(rows))
