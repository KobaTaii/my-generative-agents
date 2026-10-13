FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    git curl build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/environment/frontend_server

RUN pip install --no-cache-dir \
    django==3.2.18 \
    django-cors-headers \
    django-storages \
    numpy \
    pillow \
    pandas \
    scipy \
    scikit-learn \
    selenium \
    openai==1.12.0 \
    httpx==0.27.2 \
    pydantic \
    requests

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
