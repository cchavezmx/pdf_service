FROM python:3.11-slim-bookworm

# Instalar dependencias del sistema para wkhtmltopdf y fuentes
ENV PYTHONUNBUFFERED=True
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
ENV WKHTMLTOPDF_PATH=/usr/local/bin/wkhtmltopdf
ENV PORT=8000

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget \
        ca-certificates \
        fontconfig \
        libfontconfig1 \
        libfreetype6 \
        libpng16-16 \
        libjpeg62-turbo \
        libx11-6 \
        libxext6 \
        libxrender1 \
        xfonts-75dpi \
        xfonts-base \
    && wget -q -O /tmp/wkhtmltopdf.deb \
        https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltopdf_0.12.6.1-3.bookworm_amd64.deb \
    && dpkg -i /tmp/wkhtmltopdf.deb \
    && apt-get install -f -y --no-install-recommends \
    && rm -f /tmp/wkhtmltopdf.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar el archivo de dependencias primero para aprovechar la caché de Docker
COPY requirements.txt /app/
COPY ./static /app/static

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de los archivos del proyecto
COPY . /app/

EXPOSE 8000

# Comando para ejecutar la aplicación
CMD ["gunicorn", "--bind", ":8000", "--workers", "1", "--worker-class", "uvicorn.workers.UvicornWorker", "--threads", "8", "app:app"]
