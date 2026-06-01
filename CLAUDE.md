# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a lightweight Python FastAPI microservice that generates PDFs from HTML templates. It accepts structured JSON payloads, renders Jinja2 templates, converts the resulting HTML to PDF via `pdfkit` (which wraps `wkhtmltopdf`), and returns the PDF as a streaming response.

The service supports four distinct report types:
- **Generic invoice** (`/generate-invoice/`) — simple itemized invoice
- **Vehicle logistics report** (`/vehicle-invoice/`) — Grupo Intecsa vehicle/dispatch documentation
- **Payment receipt** (`/reporte/pagos/client-maya`) — real estate payment history for Maya/AHAL clients
- **Shipping label** (`/reporte/paqueteria`) — courier labels with embedded QR codes

## Architecture

### Request Flow
1. FastAPI receives a POST request with a JSON body validated by Pydantic models (`models/models.py`)
2. The route handler injects data into a Jinja2 template along with `static_files_path` (absolute path prefixed with `file://`)
3. `pdfkit.from_string()` converts the rendered HTML to a PDF byte stream using `wkhtmltopdf`
4. The endpoint returns a `StreamingResponse` (or `Response`) with `media_type="application/pdf"`

### Template Selection Logic
The `/reporte/pagos/client-maya` endpoint inspects the `Referer` header to choose between two templates:
- Default: `templates/maya/cliente.html`
- If referer contains `gpomaya-ma-webapp.netlify.app`: `templates/martin_maya/martin_maya.html`

### Static File Access for PDF Rendering
`wkhtmltopdf` runs in a separate process and cannot resolve relative URLs. All templates receive `static_files_path` set to `file://{os.path.abspath("static")}` so images and CSS load correctly. The `enable-local-file-access` option must be passed to `pdfkit`.

The Paqueteria endpoint generates a QR code in-memory using the `qrcode` library, base64-encodes it, and embeds it directly via a data URI (`data:image/png;base64,...`) rather than referencing a static file.

### Directory Layout
- `app.py` — All FastAPI routes and application logic
- `models/models.py` — Pydantic request/response models
- `templates/` — Jinja2 HTML templates, grouped by report type
- `static/` — Images and CSS referenced by templates during PDF generation
- `reportes.http` — Sample HTTP requests for local testing

## Development Commands

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run the development server
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Build and run with Docker
```bash
docker build -t pdf-service .
docker run -p 8000:8000 pdf-service
```

### Production run (matches Dockerfile)
```bash
gunicorn --bind :8000 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 8 app:app
```

### System dependency
`wkhtmltopdf` must be installed on the host system (or in the Docker image) for `pdfkit` to function.

## Important Notes

- There is no test suite, linter configuration, or CI/CD pipeline in this repository.
- When adding new endpoints that reference local images or CSS, always pass `static_files_path` with the `file://` protocol prefix to the template context and include `enable-local-file-access` in the pdfkit options.
- The `Paqueteria` model does not have a `codigo` field in the incoming payload but the endpoint references `invoice_data.codigo`; ensure the caller provides it in the JSON body.
