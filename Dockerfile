# Use Python 3.11 base image
FROM python:3.11-slim

# Install system dependencies for dlib and OpenCV
RUN apt-get update && \
    apt-get install -y cmake g++ make libboost-all-dev libopencv-dev ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Django project
COPY . .

# Collect static files (if needed)
RUN python manage.py collectstatic --noinput

# Expose port for Render
EXPOSE 10000

# Start the Django app
CMD ["gunicorn", "criminal_face_detection.wsgi:application", "--bind", "0.0.0.0:10000"]
