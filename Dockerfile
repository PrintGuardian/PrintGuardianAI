FROM debian:bookworm-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        python3 \
        python3-fastapi \
        python3-numpy \
        python3-opencv \
        python3-requests \
        python3-uvicorn \
    && rm -rf /var/lib/apt/lists/*
COPY backend ./backend
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
