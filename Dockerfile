FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install firefox
RUN playwright install-deps firefox

COPY main.py .

CMD ["python3", "main.py"]
