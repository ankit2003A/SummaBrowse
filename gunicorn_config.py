import multiprocessing
import os

# Number of workers = (2 x $num_cores) + 1
workers = min(2, multiprocessing.cpu_count() + 1)

# Use a sync worker class for better memory management
worker_class = 'sync'

# Timeout after 120 seconds of no activity
timeout = 120

# Maximum number of requests a worker will process before restarting
max_requests = 100
max_requests_jitter = 20

# Maximum memory usage per worker (in MB)
# This helps prevent memory leaks from consuming too much memory
worker_max_requests = 100
worker_max_requests_jitter = 20

# Set environment variables
raw_env = [
    'FLASK_ENV=production',
    'PYTHONUNBUFFERED=1',
    'TOKENIZERS_PARALLELISM=false',  # Disable tokenizer parallelism to avoid deadlocks
]

# Logging configuration
loglevel = 'info'
errorlog = '-'
accesslog = '-'
capture_output = True

# Bind to all network interfaces
bind = '0.0.0.0:' + os.environ.get('PORT', '5000')

# Preload the application to save memory
preload_app = True
