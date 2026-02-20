FROM python:3.11-slim

WORKDIR /app/project

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

CMD ["python3", "-m", "src.bot"]