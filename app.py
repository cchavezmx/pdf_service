from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import pdfkit
import os

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
