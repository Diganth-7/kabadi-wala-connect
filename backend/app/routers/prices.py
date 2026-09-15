"""
routers/prices.py
------------------
GET /api/prices             -> current prices for every material
GET /api/prices/{material_id} -> current price for one material

Like materials, prices are public reference data (no login required) —
collectors need to see prices before deciding to create a lot.

IMPORTANT: this is the ONLY place price numbers come from in the whole
app. The frontend is never trusted to supply a price — future features
(lot value estimation, etc.) all call price_service functions directly
on the backend instead of trusting any price sent in a request.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.price import PriceOut
from app.services import price_service
from app.utils.errors import success_response

router = APIRouter()


@router.get("")
def list_prices(db: Session = Depends(get_db)):
    prices = price_service.get_all_prices(db)
    data = [PriceOut.model_validate(p).model_dump(mode="json") for p in prices]
    return success_response(data)


@router.get("/{material_id}")
def get_price(material_id: str, db: Session = Depends(get_db)):
    price = price_service.get_price_by_material(db, material_id)
    return success_response(PriceOut.model_validate(price).model_dump(mode="json"))
