FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# uid 1000 matches the typical host user so the mounted ./data volume
# stays writable
RUN useradd --create-home --uid 1000 appuser && chown -R appuser /app
USER appuser

# The scheduler refreshes this file every minute; a stale file means the
# scheduler thread is wedged even if the process is still alive.
ENV HEARTBEAT_FILE=/tmp/scheduler-heartbeat

HEALTHCHECK --interval=60s --timeout=5s --start-period=30s --retries=3 \
  CMD ["python", "-c", "import os,sys,time; p=os.environ['HEARTBEAT_FILE']; sys.exit(0 if os.path.exists(p) and time.time()-os.path.getmtime(p) < 180 else 1)"]

# Runs the trend publisher on a daily schedule (see PUBLISH_TIMES).
CMD ["python", "app/trend_scheduler.py"]
