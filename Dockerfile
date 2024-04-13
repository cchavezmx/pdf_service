FROM python:3.8
# Instalar dependencias del sistema para wkhtmltopdf
ENV PYTHONUNBUFFERED True
ENV XDG_RUNTIME_DIR=/tmp/runtime-root
RUN apt-get update && apt-get install -y wkhtmltopdf

# Encuentra la ruta del binario wkhtmltopdf y configúrala como una variable de entorno
RUN ln -s $(which wkhtmltopdf) /usr/local/bin/wkhtmltopdf
ENV WKHTMLTOPDF_PATH /usr/local/bin/wkhtmltopdf

ENV PORT 8000
    
WORKDIR /app

# Copiar el archivo de dependencias primero para aprovechar la caché de Docker
COPY requirements.txt /app/

COPY ./static /app/static

# Instalar dependencias
RUN pip install -r requirements.txt

# Copiar el resto de los archivos del proyecto
COPY . /app/

# Instalar gunicorn
RUN pip install gunicorn
EXPOSE 8000


# Comando para ejecutar la aplicación
CMD exec gunicorn --bind :$PORT --workers 1 --worker-class uvicorn.workers.UvicornWorker  --threads 8 app:app
