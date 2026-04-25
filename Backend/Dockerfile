# Verwende offizielles Python-Image
FROM python:3.12-slim

# Disable .pyc bytecode files — avoids VirtioFS EDEADLK deadlocks on macOS Docker
# when Python's import system rapidly reads cached bytecode from bind mounts
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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
