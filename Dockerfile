FROM python:3.11-slim

# Install system dependencies for dlib & mysqlclient
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    g++ \
    make \
    libboost-all-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libopencv-dev \
    ffmpeg \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput || true

EXPOSE 10000

CMD ["gunicorn", "criminal_face_detection.wsgi:application", "--bind", "0.0.0.0:10000"]
