"""
routers/materials.py
---------------------
GET /api/materials — returns the fixed catalog of material types
(Copper, Aluminium, PCB, etc.). This is public reference data every
role needs (collectors need it to create lots, recyclers need it to
see what's being offered), so it doesn't require login.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.material import Material
from app.schemas.material import MaterialOut
from app.utils.errors import success_response

router = APIRouter()


@router.get("")
def list_materials(db: Session = Depends(get_db)):
    materials = db.query(Material).order_by(Material.id).all()
    data = [MaterialOut.model_validate(m).model_dump() for m in materials]
    return success_response(data)
