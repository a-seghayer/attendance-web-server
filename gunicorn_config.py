"""
Gunicorn configuration file for PreStaff API
Optimized for memory management and worker stability
"""

import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
backlog = 2048

# Worker processes - optimized for limited resources
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))  # 2 workers for 512MB RAM
worker_class = 'sync'
worker_connections = 100  # Reduced for limited resources
timeout = 60  # Reduced since batch operations are fast now
keepalive = 5

# Worker lifecycle and memory management
max_requests = 50  # More aggressive restart to prevent memory leaks on limited resources
max_requests_jitter = 10  # Add randomness to prevent all workers restarting at once
graceful_timeout = 30  # Reduced since operations should complete faster now

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
