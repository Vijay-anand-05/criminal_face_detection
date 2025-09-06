FROM python:3.11-slim

# Install system dependencies for dlib, face_recognition, mysqlclient
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

# Install latest CMake (needed for dlib build)
RUN wget -qO- https://cmake.org/files/v3.29/cmake-3.29.6-linux-x86_64.tar.gz \
    | tar --strip-components=1 -xz -C /usr/local

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files for Django
RUN python manage.py collectstatic --noinput

EXPOSE 10000

CMD ["gunicorn", "criminal_face_detection.wsgi:application", "--bind", "0.0.0.0:10000"]
