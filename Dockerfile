FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md openapi.yaml ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

EXPOSE 8000
CMD ["uvicorn","cbsrmt_api.main:app","--host","0.0.0.0","--port","8000"]
