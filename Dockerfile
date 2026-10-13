FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    git curl build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir \
    django==3.2.18 \
    openai==1.12.0 \
    httpx \
    pydantic \
    requests

CMD ["python", "environment/frontend_server/manage.py", "runserver", "0.0.0.0:8000"]
