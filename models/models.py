from pydantic import BaseModel, EmailStr, Field
from typing import List
from typing import Optional
from datetime import date

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
    isCancel_status: str

class Cliente(BaseModel):
    nombre: str
    email: EmailStr
    telefono: Optional[str] = "No Data"
    direccion: Optional[str] = "No Data"

class Proyecto(BaseModel):
    titulo: str
    activo: bool

class Lote(BaseModel):
    lote_numero: int = Field(..., alias='lote_numero')
    precio_total: float = Field(..., alias='precio_total')
    enganche: float
    financiamiento: float
    plazo: int
    mensualidad: float
    inicio_contrato: date = Field(..., alias='inicio_contrato')
class Pago(BaseModel):
    fecha: date
    folio: int
    mensualidad: float
    refPago: str
    refBanco: int
    ctaBancaria: int
    banco: str
class PagosMaya(BaseModel):
    cliente: Cliente
    proyecto: Proyecto
    lote: Lote
    pagos: List[Pago]  # Añadir esto

class Paqueteria(BaseModel):
    id: str
    proyecto: str
    paqueteria: str
    direccion: str
    contacto: str
    numeroContacto: str
    empresaEnvio: str
    contacto_recibe: str
    numeroContacto_recibe: str
    contacto_recibe_email: str
    emailContacto: str
    createdAt: str
    codigo: str

