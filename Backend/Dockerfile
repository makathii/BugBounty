# Verwende offizielles Python-Image
FROM python:3.12-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# Dependencies installieren
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Projektdateien kopieren
COPY . .

# Port für Django
EXPOSE 8000

# Standardbefehl
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
