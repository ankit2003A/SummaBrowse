# Gunicorn configuration file
import multiprocessing

# Server socket
bind = "0.0.0.0:10000"

# Worker processes
workers = 2
threads = 2
worker_class = 'gthread'
worker_connections = 1000

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Timeouts
timeout = 120
keepalive = 5
