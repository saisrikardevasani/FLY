# Build stage: install the dependencies into a staging prefix.
FROM python:3.11-slim AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Runtime stage: copy only what was installed, so pip's own working files never ship.
FROM python:3.11-slim
WORKDIR /app
COPY --from=build /install /usr/local
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000"]
