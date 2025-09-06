# Use Python 3.11 base image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y cmake g++ make libboost-all-dev libopencv-dev ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy Django project
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

EXPOSE 10000

CMD ["gunicorn", "criminal_face_detection.wsgi:application", "--bind", "0.0.0.0:10000"]
