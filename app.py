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

        # Actualizar la fecha en los datos de la factura
        invoice_data_dict = invoice_data.dict(by_alias=True)

        # Renderizar la plantilla HTML con los datos proporcionados
        html_content = templates.TemplateResponse("intecsa/vehicles.html", {
            "request": request,
            # Usar el diccionario actualizado con la fecha formateada
            "details": invoice_data_dict
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
    try:
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        static_files_path = os.path.abspath("static")
        html_content = templates.TemplateResponse("maya/cliente.html", {
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
