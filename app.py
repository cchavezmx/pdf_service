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


def _round_money(value) -> float:
    """Redondea a 2 decimales (espejo de roundMoney en utils/costBreakdown.js)."""
    return round(float(value), 2)


def compute_dias_periodo(request_day, delivery_day) -> int:
    """Días entre request_day y delivery_day (mínimo 1), para defaults de
    conceptos por día. Tolerante a formatos de fecha."""
    if not request_day or not delivery_day:
        return 1
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            req = datetime.strptime(str(request_day).strip(), fmt)
            deliv = datetime.strptime(str(delivery_day).strip(), fmt)
            diff = (deliv - req).days
            return diff if diff > 0 else 1
        except (ValueError, TypeError):
            continue
    return 1


def _concept_importe(rate, unit, qty, dias_periodo=1, fixed=False):
    """Importe por concepto desde tarifas crudas. Espejo de computeConceptTotal
    en utils/costBreakdown.js del wizard; solo se usa como fallback cuando el
    payload no trae el *_importe ya calculado."""
    rate = rate or 0
    if not rate:
        return 0.0
    if fixed or unit == "fijo":
        return _round_money(rate)
    qty = qty or 0
    if not qty:
        qty = dias_periodo or 1
    return _round_money(rate * qty)


def _gasoline_importe(rate, unit, km):
    """Gasolina: monto fijo salvo unidad 'km' con km > 0 (espejo del wizard)."""
    rate = rate or 0
    if not rate:
        return 0.0
    if unit == "km" and (km or 0) > 0:
        return _round_money(rate * (km or 0))
    return _round_money(rate)


def _build_breakdown_rows(cb, importes, dias_periodo=1):
    """Renglones del desglose. Las tarifas crudas solo arman los textos
    ("40 día × $430.00"); el importe siempre es el final (verbatim o fallback)."""
    rows = []

    if importes["casetas"] > 0:
        notes = cb.casetas_notes or ""
        unit_label = f"Monto fijo" + (f" — {notes}" if notes else "")
        rows.append({"concepto": "Casetas", "unidad": unit_label, "importe": importes["casetas"]})

    if importes["operator"] > 0:
        op_days = cb.operator_days or (0 if cb.operator_unit == "fijo" else dias_periodo)
        unit_label = f"{op_days} días × {fmt_money(cb.operator_rate)}/día" if op_days else "Monto fijo"
        rows.append({"concepto": "Operador", "unidad": unit_label, "importe": importes["operator"]})

    if importes["per_diem"] > 0:
        pd_days = cb.per_diem_days or (0 if cb.per_diem_unit == "fijo" else dias_periodo)
        unit_label = f"{pd_days} días × {fmt_money(cb.per_diem_rate)}/día" if pd_days else "Monto fijo"
        rows.append({"concepto": "Viáticos", "unidad": unit_label, "importe": importes["per_diem"]})

    if importes["gasoline"] > 0:
        if cb.gasoline_unit == "km" and cb.gasoline_km and cb.gasoline_km > 0:
            unit_label = f"{cb.gasoline_km} km × {fmt_money(cb.gasoline_rate)}/km"
        elif cb.gasoline_km and cb.gasoline_km > 0:
            unit_label = f"Monto fijo ({cb.gasoline_km} km recorrido)"
        else:
            unit_label = "Monto fijo"
        rows.append({"concepto": "Gasolina", "unidad": unit_label, "importe": importes["gasoline"]})

    if importes["unit_rent"] > 0:
        rent_label = {"dia": "Renta por día", "semana": "Renta por semana", "mes": "Renta por mes"}.get(cb.unit_rent_period, "Renta de unidad")
        qty = cb.unit_rent_qty or (0 if cb.unit_rent_unit == "fijo" else dias_periodo)
        if qty and cb.unit_rent_amount:
            unit_label = f"{qty} {cb.unit_rent_period or 'dia'} × {fmt_money(cb.unit_rent_amount)}"
        else:
            unit_label = f"Por {cb.unit_rent_period or 'dia'}"
        rows.append({"concepto": rent_label, "unidad": unit_label, "importe": importes["unit_rent"]})

    return rows


def build_cost_breakdown(cb, profit_pct=8, indirect_pct=12, dias_periodo=1):
    """Build breakdown rows and totals from a CostBreakdown object.

    Regla de negocio: el servicio de PDF no recalcula. Si el wizard/API ya
    envió los montos finales (*_importe, subtotal_amount, base_amount,
    iva_amount, total_amount), se renderizan tal cual. La fórmula de fallback
    (con renta × unit_rent_qty) solo aplica a documentos legacy sin montos.
    """
    breakdown = {
        "rows": [], "subtotal": 0.0, "profit": 0.0, "indirect": 0.0,
        "base": 0.0, "iva": 0.0, "total": 0.0, "has_breakdown": False
    }
    if not cb:
        return breakdown

    # Importes por concepto: verbatim si el wizard los envió; si falta
    # alguno (payload parcial), se calcula desde las tarifas crudas.
    importes = {
        "casetas": cb.casetas_importe if cb.casetas_importe is not None
                   else _concept_importe(cb.casetas_amount, cb.casetas_unit, 0, fixed=True),
        "operator": cb.operator_importe if cb.operator_importe is not None
                    else _concept_importe(cb.operator_rate, cb.operator_unit, cb.operator_days, dias_periodo),
        "per_diem": cb.per_diem_importe if cb.per_diem_importe is not None
                    else _concept_importe(cb.per_diem_rate, cb.per_diem_unit, cb.per_diem_days, dias_periodo),
        "gasoline": cb.gasoline_importe if cb.gasoline_importe is not None
                    else _gasoline_importe(cb.gasoline_rate, cb.gasoline_unit, cb.gasoline_km),
        "unit_rent": cb.unit_rent_importe if cb.unit_rent_importe is not None
                     else _concept_importe(cb.unit_rent_amount, cb.unit_rent_unit, cb.unit_rent_qty, dias_periodo),
    }
    rows = _build_breakdown_rows(cb, importes, dias_periodo)

    if cb.total_amount is not None and cb.subtotal_amount is not None:
        # Modo desglose: montos finales del wizard, verbatim.
        subtotal = cb.subtotal_amount
        # Sanidad opcional (no corrige, no falla): el subtotal debe cuadrar
        # con la suma de los *_importe que llegaron en el payload.
        verbatim = [cb.casetas_importe, cb.operator_importe, cb.per_diem_importe,
                    cb.gasoline_importe, cb.unit_rent_importe]
        verbatim = [v for v in verbatim if v is not None]
        if verbatim:
            verbatim_sum = _round_money(sum(verbatim))
            if abs(subtotal - verbatim_sum) > 0.01:
                print(f"[cost_breakdown] discrepancia: subtotal_amount={subtotal} "
                      f"!= suma *_importe={verbatim_sum}")
    else:
        # Fallback legacy: fórmula corregida (renta × qty, gasolina fija).
        subtotal = _round_money(sum(importes.values()))

    # Utilidad/indirectos: persistidos tal cual; recalcular solo si no existen.
    profit = cb.profit_amount if cb.profit_amount is not None \
        else _round_money(subtotal * (profit_pct or 8) / 100)
    indirect = cb.indirect_amount if cb.indirect_amount is not None \
        else _round_money(subtotal * (indirect_pct or 12) / 100)

    base = cb.base_amount if cb.base_amount is not None \
        else _round_money(subtotal + profit + indirect)
    iva = cb.iva_amount if cb.iva_amount is not None \
        else _round_money(base * 0.16)
    total = cb.total_amount if cb.total_amount is not None \
        else _round_money(base + iva)

    breakdown.update({
        "rows": rows,
        "subtotal": subtotal,
        "profit": profit,
        "indirect": indirect,
        "base": base,
        "iva": iva,
        "total": total,
        "has_breakdown": len(rows) > 0
    })
    return breakdown


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

        # Construir desglose de conceptos según el modo
        if invoice_data.snapshot_mode:
            rows = []
            for item in (invoice_data.line_items or []):
                rows.append({
                    "concepto": item.label,
                    "unidad": item.unit or "—",
                    "importe": item.total or 0,
                    "unit_price": item.unit_price or 0,
                    "qty": item.qty or 0,
                    "notes": item.notes or ""
                })
            totals = invoice_data.totals or Totals()
            breakdown = {
                "rows": rows,
                "subtotal": totals.concepts_subtotal or 0,
                "subtotal_travel": totals.subtotal_travel or 0,
                "profit": totals.profit_amount or 0,
                "indirect": totals.indirect_amount or 0,
                "total": totals.grand_total or 0,
                "grand_total": totals.grand_total or 0,
                "has_breakdown": len(rows) > 0,
                "snapshot_mode": True
            }
        else:
            dias_periodo = compute_dias_periodo(invoice_data.request_day, invoice_data.delivery_day)
            breakdown = build_cost_breakdown(
                invoice_data.cost_breakdown,
                profit_pct=invoice_data.profit_pct or 8,
                indirect_pct=invoice_data.indirect_pct or 12,
                dias_periodo=dias_periodo
            )
            breakdown["snapshot_mode"] = False

        # Preparar datos de pre-flight
        pre_flight_data = build_pre_flight(invoice_data.pre_flight, invoice_data.cargo_description)

        # Renderizar la plantilla HTML con los datos proporcionados
        html_content = templates.TemplateResponse("intecsa/vehicles.html", {
            "request": request,
            "details": invoice_data_dict,
            "breakdown": breakdown,
            "pre_flight_data": pre_flight_data,
            "fmt_money": fmt_money,
            "snapshot_mode": invoice_data.snapshot_mode
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
