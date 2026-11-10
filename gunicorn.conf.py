import os

# Render sets $PORT; default to 10000 for local Docker runs.
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# One worker keeps memory low on Render's 512 MB free instance; threads handle concurrency.
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"

# Video transcription can take a few minutes.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "300"))
keepalive = 5

accesslog = "-"
errorlog = "-"
loglevel = "info"
