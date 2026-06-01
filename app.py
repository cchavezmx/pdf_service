from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.responses import StreamingResponse
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from models.models import *
import pdfkit
import os
import io
from io import BytesIO
import base64
from typing import Optional
import qrcode


def fmt_money(value: float) -> str:
    """Format a number as Mexican pesos string."""
    if value is None:
        return "$0.00"
    return f"${value:,.2f}"


def build_cost_breakdown(cb):
    """Build breakdown rows and totals from a CostBreakdown object."""
    rows = []
    if not cb:
        return {"rows": [], "subtotal": 0.0, "iva": 0.0, "total": 0.0, "has_breakdown": False}

    if cb.casetas_amount and cb.casetas_amount > 0:
        rows.append({"concepto": "Casetas", "unidad": "—", "importe": cb.casetas_amount})

    if cb.operator_rate and cb.operator_rate > 0 and cb.operator_days and cb.operator_days > 0:
        amount = cb.operator_rate * cb.operator_days
        rows.append({"concepto": "Operador", "unidad": f"{cb.operator_days} días × {fmt_money(cb.operator_rate)}/día", "importe": amount})

    if cb.per_diem_rate and cb.per_diem_rate > 0 and cb.per_diem_days and cb.per_diem_days > 0:
        amount = cb.per_diem_rate * cb.per_diem_days
        rows.append({"concepto": "Viáticos", "unidad": f"{cb.per_diem_days} días × {fmt_money(cb.per_diem_rate)}/día", "importe": amount})

    if cb.gasoline_rate and cb.gasoline_rate > 0 and cb.gasoline_km and cb.gasoline_km > 0:
        amount = cb.gasoline_rate * cb.gasoline_km
        rows.append({"concepto": "Gasolina", "unidad": f"{cb.gasoline_km} km × {fmt_money(cb.gasoline_rate)}/km", "importe": amount})

    if cb.unit_rent_amount and cb.unit_rent_amount > 0:
        period_label = {"dia": "Por día", "semana": "Por semana", "mes": "Por mes"}.get(cb.unit_rent_period, "—")
        rows.append({"concepto": "Renta de unidad", "unidad": period_label, "importe": cb.unit_rent_amount})

    if cb.profit_amount and cb.profit_amount > 0:
        rows.append({"concepto": "Utilidad", "unidad": "—", "importe": cb.profit_amount})

    if cb.indirect_amount and cb.indirect_amount > 0:
        rows.append({"concepto": "Indirectos", "unidad": "—", "importe": cb.indirect_amount})

    subtotal = sum(r["importe"] for r in rows)
    iva = round(subtotal * 0.16 * 100) / 100
    total = round((subtotal + iva) * 100) / 100

    return {
        "rows": rows,
        "subtotal": subtotal,
        "iva": iva,
        "total": total,
        "has_breakdown": len(rows) > 0
    }


def build_pre_flight(pf, top_level_cargo: str):
    """Build pre-flight data for the template."""
    if not pf:
        return {"has_pre_flight": False}

    items = []
    if pf.items:
        items = [
            {"label": "Extintor", "value": pf.items.extintor},
            {"label": "Llanta de refacción", "value": pf.items.llanta_refaccion},
            {"label": "Herramientas", "value": pf.items.herramientas},
            {"label": "Gato y cruceta", "value": pf.items.gato},
            {"label": "Cinturón", "value": pf.items.cinturon},
            {"label": "Documentos", "value": pf.items.documentos},
            {"label": "Tarjetas", "value": pf.items.tarjetas},
        ]

    cargo = top_level_cargo or (pf.cargo_description if pf else "")

    return {
        "has_pre_flight": True,
        "fuel_level": pf.fuel_level,
        "cargo": cargo,
        "observaciones": pf.observaciones,
        "checklist": items
    }


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
        html_content = templates.TemplateResponse(
            "factura/index.html", context).body.decode("utf-8")

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
        # Convertir a diccionario
        invoice_data_dict = invoice_data.dict(by_alias=True)

        # Calcular desglose de conceptos
        breakdown = build_cost_breakdown(invoice_data.cost_breakdown)

        # Preparar datos de pre-flight
        pre_flight_data = build_pre_flight(invoice_data.pre_flight, invoice_data.cargo_description)

        # Renderizar la plantilla HTML con los datos proporcionados
        html_content = templates.TemplateResponse("intecsa/vehicles.html", {
            "request": request,
            "details": invoice_data_dict,
            "breakdown": breakdown,
            "pre_flight_data": pre_flight_data,
            "fmt_money": fmt_money
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


@app.post("/reporte/pagos/client-maya", response_class=StreamingResponse)
async def create_invoice(request: Request, invoice_data: PagosMaya):

    template = "maya/cliente.html"
    referer = request.headers.get("referer")

    if "gpomaya-ma-webapp.netlify.app" in referer:
        template = "martin_maya/martin_maya.html"

    try:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        static_files_path = os.path.abspath("static")
        html_content = templates.TemplateResponse(template, {
            "request": request,
            "cliente": invoice_data.cliente,
            "proyecto": invoice_data.proyecto,
            "lote": invoice_data.lote,
            "pagos": invoice_data.pagos,  # Asegúrate de pasar la lista de pagos
            "fecha_actual": fecha_actual,
            "static_files_path": f"file://{static_files_path}"
        }).body.decode("utf-8")

        # Opciones para wkhtmltopdf
        options = {
            'enable-local-file-access': None
        }

        # Convertir el HTML a PDF
        pdf = pdfkit.from_string(html_content, False, options=options)

        # Envolver el PDF en BytesIO
        pdf_io = io.BytesIO(pdf)

        # Devolver el PDF como respuesta de flujo
        return StreamingResponse(pdf_io, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=invoice.pdf"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Error al generar la factura: {str(e)}"}
        )


@app.post("/reporte/paqueteria", response_class=StreamingResponse)
async def create_invoice(request: Request, invoice_data: Paqueteria):
    try:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        static_files_path = os.path.abspath("static")

        # Generar el código QR
        order_id = invoice_data.id
        baser_url = "https://control-fletes.vercel.app/paqueterita/attempt/"
        dynamic_url = f"{baser_url}/{order_id}"

        # Generar el QR a partir de la URL
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(dynamic_url)
        qr.make(fit=True)

        # Guardar el QR como imagen en memoria
        qr_img = BytesIO()
        qr.make_image(fill="black", back_color="white").save(
            qr_img, format="PNG")
        qr_img_base64 = base64.b64encode(qr_img.getvalue()).decode('utf-8')
        qr_img.close()

        html_content = templates.TemplateResponse("paqueteria/invoice.html", {
            "request": request,
            "proyecto": invoice_data.proyecto,
            "paqueteria": invoice_data.paqueteria,
            "direccion": invoice_data.direccion,
            "contacto": invoice_data.contacto,
            "numeroContacto": invoice_data.numeroContacto,
            "empresaEnvio": invoice_data.empresaEnvio,
            "contacto_recibe": invoice_data.contacto_recibe,
            "numeroContacto_recibe": invoice_data.numeroContacto_recibe,
            "codigo": invoice_data.codigo,
            "fecha": fecha_actual,
            "createdAt": invoice_data.createdAt,
            "contacto_recibe_email": invoice_data.contacto_recibe_email,
            "emailContacto": invoice_data.emailContacto,
            "static_files_path": f"file://{static_files_path}",
            "qr_code": f"data:image/png;base64,{qr_img_base64}"
        }).body.decode("utf-8")

        options = {
            'enable-local-file-access': None
        }

        pdf = pdfkit.from_string(html_content, False, options=options)
        pdf_io = io.BytesIO(pdf)

        return StreamingResponse(pdf_io, media_type="application/pdf", headers={
            "Content-Disposition": f"attachment; filename=invoice.pdf"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": f"Error al generar la factura: {str(e)}"}
        )
