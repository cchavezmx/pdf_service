from pydantic import BaseModel
from typing import Optional

class Description(BaseModel):
    link_googlemaps: str
    document_id: str
    project_id: str
    planDescription: str
    planPrice: str

class VehicleInfo(BaseModel):
    name: str
    placas: str
    driver: str
    fuel_card: str
    fuel_amount: str

class InvoiceData(BaseModel):
    type: str
    currentEmpresa: str
    folio: int
    created_day: str
    request_day: str
    delivery_day: str
    currentClient: str
    subject: Optional[str] = None
    vehicle: VehicleInfo
    route: str
    kilometer_out: int
    fuel_level: int
    recorrido_km: str
    description: Description
    subtotal_travel: str
