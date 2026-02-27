# main.py
from datetime import date, datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Generic Carrier Rate Quote (Mock)")

class RateRequest(BaseModel):
    product: str = Field(..., min_length=1)
    weightKg: float = Field(..., gt=0)
    # Accepted input formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD (ISO),
    # datetimes (ISO with time), or epoch seconds. The service will
    # normalize/output the date as DD-MM-YYYY.
    expectedDeliveryOn: str = Field(
        ...,
        description=(
            'Accepted input formats: "DD-MM-YYYY", "DD/MM/YYYY", "YYYY-MM-DD", '
            'ISO datetimes (e.g. "2026-02-27T15:00:00"), or epoch seconds. '
            'Output will be standardized to "DD-MM-YYYY".'
        ),
    )

class PriceBreakdown(BaseModel):
    baseFee: float
    weightFee: float
    urgencyFee: float
    productSurcharge: float

class RateResponse(BaseModel):
    currency: str
    totalPrice: float
    breakdown: PriceBreakdown
    etaDate: str  # <- will be "DD-MM-YYYY"

def parse_date(s) -> date:
    """Parse multiple common date formats and return a date object.

    Accepts:
    - strings in formats: DD-MM-YYYY, DD/MM/YYYY, YYYY-MM-DD
    - ISO datetime strings (with time and optional offset)
    - numeric epoch seconds (int or string of digits)
    - datetime/date objects (returned as date)

    Raises HTTPException(422) when parsing fails.
    """
    if isinstance(s, date) and not isinstance(s, datetime):
        return s

    # If it's a datetime, convert to date
    if isinstance(s, datetime):
        return s.date()

    if s is None:
        raise HTTPException(422, 'expectedDeliveryOn is required')

    s_str = str(s).strip()

    # Try epoch seconds
    if s_str.isdigit():
        try:
            ts = int(s_str)
            return datetime.fromtimestamp(ts).date()
        except (OverflowError, OSError, ValueError):
            # fall through to other parsers
            pass

    # Try ISO parse
    try:
        # datetime.fromisoformat handles YYYY-MM-DD and many ISO variants
        d = datetime.fromisoformat(s_str)
        return d.date()
    except Exception:
        pass

    # Common explicit formats to try
    fmts = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d %b %Y",
        "%d %B %Y",
        "%d-%m-%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in fmts:
        try:
            return datetime.strptime(s_str, fmt).date()
        except ValueError:
            continue

    raise HTTPException(
        422,
        'expectedDeliveryOn could not be parsed. Accepted: DD-MM-YYYY, DD/MM/YYYY, '
        'YYYY-MM-DD (ISO), ISO datetimes, or epoch seconds',
    )

def to_ddmmyyyy(d: date) -> str:
    return d.strftime("%d-%m-%Y")

def compute_mock_price(product: str, weight_kg: float, expected_delivery: date) -> RateResponse:
    base_fee = 80.0
    weight_fee = 55.0 * weight_kg

    days_until = (expected_delivery - date.today()).days
    urgency_fee = 0.0 if days_until >= 5 else (120.0 if days_until >= 2 else 220.0)

    p = product.strip().lower()
    product_surcharge = 75.0 if p in {"laptop", "phone", "tablet"} else 0.0

    total = round(base_fee + weight_fee + urgency_fee + product_surcharge, 2)

    return RateResponse(
        currency="INR",
        totalPrice=total,
        breakdown=PriceBreakdown(
            baseFee=round(base_fee, 2),
            weightFee=round(weight_fee, 2),
            urgencyFee=round(urgency_fee, 2),
            productSurcharge=round(product_surcharge, 2),
        ),
        etaDate=to_ddmmyyyy(expected_delivery),  # <- formatted as DD-MM-YYYY
    )

@app.post("/v1/rates/quote", response_model=RateResponse)
def quote_rate(req: RateRequest):
    expected_delivery = parse_date(req.expectedDeliveryOn)
    return compute_mock_price(req.product, req.weightKg, expected_delivery)
