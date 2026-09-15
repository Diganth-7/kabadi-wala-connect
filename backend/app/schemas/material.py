"""
schemas/material.py
--------------------
Response shape for materials — mirrors the Material model but keeps
the schema separate from the DB model on purpose. This way, if we ever
add internal-only columns to the Material table later, they don't
automatically leak into the API response just because we forgot to
update a schema.
"""

from pydantic import BaseModel


class MaterialOut(BaseModel):
    id: str
    name: str
    display_name: str
    icon: str | None = None
    unit: str

    model_config = {"from_attributes": True}
