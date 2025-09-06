FROM python:3.11-slim

# Install system dependencies for face_recognition + mysqlclient
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    make \
    libboost-all-dev \
    libopencv-dev \
    ffmpeg \
    default-libmysqlclient-dev \
    pkg-config \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install prebuilt dlib wheel from PyPI instead of compiling
RUN pip install --upgrade pip \
    && pip install --no-cache-dir dlib==19.24.2 --only-binary=:all: \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files for Django
RUN python manage.py collectstatic --noinput

EXPOSE 10000

CMD ["gunicorn", "criminal_face_detection.wsgi:application", "--bind", "0.0.0.0:10000"]
