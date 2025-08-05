# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "0.0.0.0:10000"

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 3
worker_connections = 1000

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Timeouts
timeout = 120
keepalive = 5
