from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime
import pdfkit
import os
import io
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
    subject: Optional[str] = None  # Suponiendo que este campo puede ser opcional.
    vehicle: VehicleInfo
    route: str
    kilometer_out: int
    fuel_level: int
    recorrido_km: int
    description: Description
    subtotal_travel: str

app = FastAPI()
templates = Jinja2Templates(directory="templates")
# Asegúrate de montar el directorio estático de FastAPI
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.post("/generate-invoice/")
async def generate_invoice(request: Request, details: dict, items: dict):
    try:
        # Construye la ruta absoluta al archivo estático que necesitas
        static_files_path = os.path.abspath("static")
        
        # Añade la ruta al contexto para usarla en la plantilla
        context = {
            "request": request,
            "details": details,
            "items": items,
            "static_files_path": f"file://{static_files_path}"
        }
        
        # Renderiza la plantilla HTML con los datos proporcionados
        html_content = templates.TemplateResponse("factura/index.html", context).body.decode("utf-8")

        # Opciones para permitir el acceso a archivos locales en wkhtmltopdf
        options = {
            'enable-local-file-access': None
        }

        # Usa pdfkit para convertir el HTML renderizado en PDF
        pdf = pdfkit.from_string(html_content, False, options=options)

        # Retorna el PDF como respuesta
        return Response(content=pdf, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/vehicle-invoice/", response_class=StreamingResponse)
async def create_invoice(request: Request, invoice_data: InvoiceData):
    try:
                
        # Actualizar la fecha en los datos de la factura
        invoice_data_dict = invoice_data.dict(by_alias=True)        
        
        # Renderizar la plantilla HTML con los datos proporcionados
        html_content = templates.TemplateResponse("intecsa/vehicles.html", {
            "request": request,
            "details": invoice_data_dict  # Usar el diccionario actualizado con la fecha formateada
        }).body.decode("utf-8")

        # Opciones para permitir el acceso a archivos locales en wkhtmltopdf
        options = {
            'enable-local-file-access': None
        }

        # Usa pdfkit para convertir el HTML renderizado en PDF
        pdf = pdfkit.from_string(html_content, False, options=options)

        # Envuelve el PDF en un objeto BytesIO para que se pueda transmitir
        pdf_io = io.BytesIO(pdf)

        # Crea y devuelve una respuesta de flujo de StreamingResponse
        return StreamingResponse(pdf_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=invoice.pdf"
        })
    except Exception as e:
        # Devuelve una respuesta JSON en caso de error
        return JSONResponse(
            status_code=500,
            content={"message": f"Error al generar la factura: {str(e)}"}
        )