FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Runs the trend publisher on a daily schedule (see PUBLISH_TIMES).
CMD ["python", "app/trend_scheduler.py"]
