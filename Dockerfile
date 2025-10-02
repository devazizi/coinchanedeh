FROM python:3.12.11-slim-bookworm

WORKDIR /app

COPY requirements.txt requirements.txt

COPY app.py app.py

RUN pip install -r requirements.txt --no-cache-dir

ENTRYPOINT ["python", "app.py"]