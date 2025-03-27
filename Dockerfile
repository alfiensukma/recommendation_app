# Gunakan base image Python
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Instal dependensi sistem (jika diperlukan)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Salin dan instal dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh proyek
COPY . .

# Jalankan Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "recommendation_app.wsgi:application"]
