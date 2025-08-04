import multiprocessing
import os

# Server socket
bind = '0.0.0.0:' + os.environ.get('PORT', '10000')

# Worker processes - Reduced for Render's free tier
workers = 1
worker_class = 'sync'
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
worker_max_requests = 1000
worker_max_requests_jitter = 100

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Debugging
reload = os.environ.get('FLASK_ENV') == 'development'
reload_engine = 'auto'

# Server mechanics
preload_app = True

# Logging
loglevel = os.environ.get('LOG_LEVEL', 'info')
accesslog = '-'
errorlog = '-'
capture_output = True

# Environment variables
raw_env = [
    'FLASK_ENV=production',
    'PYTHONUNBUFFERED=1',
    'PYTHONDONTWRITEBYTECODE=1',
    'TOKENIZERS_PARALLELISM=false',
    'PYTHONHASHSEED=random',
]
