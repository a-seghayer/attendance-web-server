"""
Gunicorn configuration file for PreStaff API
Optimized for memory management and worker stability
"""

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))  # Reduced from default
worker_class = 'sync'
worker_connections = 1000
timeout = 120  # Increased timeout for large Excel uploads
keepalive = 5

# Worker lifecycle and memory management
max_requests = 100  # Restart worker after 100 requests to prevent memory leaks
max_requests_jitter = 20  # Add randomness to prevent all workers restarting at once
graceful_timeout = 60  # Give workers 60s to finish current requests before forcefully killing

# Logging
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'prestaff_api'

# Preload application
preload_app = False  # Set to False to reduce memory usage

# Worker restart on code changes (for development)
reload = os.environ.get('ENV', 'production') == 'development'

def post_fork(server, worker):
    """Called just after a worker has been forked"""
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def pre_fork(server, worker):
    """Called just before a worker is forked"""
    pass

def pre_exec(server):
    """Called just before a new master process is forked"""
    server.log.info("Forked child, re-executing.")

def when_ready(server):
    """Called just after the server is started"""
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    """Called when a worker receives INT or QUIT signal"""
    worker.log.info("Worker received INT or QUIT signal")

def worker_abort(worker):
    """Called when a worker receives SIGABRT signal (out of memory)"""
    worker.log.error(f"Worker received SIGABRT (pid: {worker.pid}) - likely out of memory")
