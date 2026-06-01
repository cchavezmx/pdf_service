from pydantic import BaseModel, EmailStr, Field
from typing import List
from typing import Optional
from datetime import date


class Description(BaseModel):
    link_googlemaps: Optional[str] = ""
    document_id: Optional[str] = ""
    project_id: Optional[str] = ""
    planDescription: Optional[str] = ""
    planPrice: Optional[str] = ""


class VehicleInfo(BaseModel):
    name: Optional[str] = ""
    placas: Optional[str] = ""
    driver: Optional[str] = ""
    fuel_card: Optional[str] = ""
    fuel_amount: Optional[str] = ""


class CostBreakdown(BaseModel):
    casetas_amount: Optional[float] = 0
    operator_rate: Optional[float] = 0
    operator_days: Optional[int] = 0
    per_diem_rate: Optional[float] = 0
    per_diem_days: Optional[int] = 0
    gasoline_rate: Optional[float] = 0
    gasoline_km: Optional[float] = 0
    unit_rent_amount: Optional[float] = 0
    unit_rent_period: Optional[str] = "dia"
    profit_amount: Optional[float] = 0
    indirect_amount: Optional[float] = 0


class PreFlightItems(BaseModel):
    extintor: Optional[bool] = True
    llanta_refaccion: Optional[bool] = True
    herramientas: Optional[bool] = True
    gato: Optional[bool] = True
    cinturon: Optional[bool] = True
    documentos: Optional[bool] = True
    tarjetas: Optional[bool] = True


class PreFlight(BaseModel):
    fuel_level: Optional[int] = 50
    cargo_description: Optional[str] = ""
    items: Optional[PreFlightItems] = None
    observaciones: Optional[str] = ""


class InvoiceData(BaseModel):
    type: str
    currentEmpresa: str
    folio: int
    created_day: str
    request_day: str
    delivery_day: str
    currentClient: str
    subject: Optional[str] = None
    vehicle: Optional[VehicleInfo] = None
    route: Optional[str] = ""
    kilometer_out: Optional[int] = 0
    fuel_level: Optional[int] = 0
    recorrido_km: Optional[str] = ""
    description: Optional[Description] = None
    subtotal_travel: Optional[str] = ""
    isCancel_status: Optional[str] = ""
    cost_breakdown: Optional[CostBreakdown] = None
    pre_flight: Optional[PreFlight] = None
    profit_pct: Optional[float] = 8
    indirect_pct: Optional[float] = 12
    cargo_description: Optional[str] = ""


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
    pagos: List[Pago]


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
