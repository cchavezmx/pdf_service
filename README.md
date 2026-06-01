# pdf_fastapi

A PDF ticket generator served through FastAPI. Renders Jinja2 HTML templates and converts them to PDF using `pdfkit` + `wkhtmltopdf`.

---

## Requirements

- Python 3.8+
- `wkhtmltopdf` system binary (required by `pdfkit`)

### System dependency

Install `wkhtmltopdf` on your OS before running the app:

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y wkhtmltopdf

# macOS
brew install --cask wkhtmltopdf
```

---

## Install

```bash
pip install -r requirements.txt
```

---

## Run locally (development)

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

---

## Run with Docker

```bash
docker build -t pdf-service .
docker run -p 8000:8000 pdf-service
```

---

## Run in production

```bash
gunicorn --bind :8000 --workers 1 --worker-class uvicorn.workers.UvicornWorker --threads 8 app:app
```

---

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate-invoice/` | POST | Generic itemized invoice |
| `/vehicle-invoice/` | POST | Vehicle logistics report (Grupo Intecsa) |
| `/reporte/pagos/client-maya` | POST | Real estate payment receipt |
| `/reporte/paqueteria` | POST | Shipping label with QR code |

See `reportes.http` for sample request payloads.
