# pylint: disable=invalid-name
"""
WoePlanet Spelunker Docker gunicorn configuration settings
"""

import multiprocessing
import setproctitle    # pylint: disable=unused-import # noqa: F401

# Server Mechanics: https://docs.gunicorn.org/en/latest/settings.html#server-mechanics
daemon = False
pidfile = 'run/api.pid'
umask = 0o644
worker_tmp_dir = '/dev/shm'
forwarded_allow_ips = '*'

# Worker Processes: https://docs.gunicorn.org/en/latest/settings.html#worker-processes
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 2
max_requests = 1000
# worker_class = 'uvicorn.workers.UvicornWorker'

# Logging: https://docs.gunicorn.org/en/stable/settings.html#logging
# Disable accesslog; route logging is handled by RouteLoggerMiddleware in the application itself
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Process naming: https://docs.gunicorn.org/en/stable/settings.html#process-naming
proc_name = 'woeplanet-spelunker'
