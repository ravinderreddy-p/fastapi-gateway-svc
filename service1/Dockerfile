# Dockerfile.service1
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10

WORKDIR /app

COPY ./main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
