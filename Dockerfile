FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

RUN which chromium || which chromium-browser || find / -name "chromium*" 2>/dev/null
RUN which chromedriver || find / -name "chromedriver*" 2>/dev/null

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .

CMD ["python3", "main.py"]
