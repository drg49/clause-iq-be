from concurrent.futures import ThreadPoolExecutor


# Demo / Portfolio App Architecture Note:
# This app is built to handle low-concurrency demo traffic (1–3 simultaneous users).
# Using a ThreadPoolExecutor (4 worker threads per process) is sufficient for handling 
# non-blocking background tasks without adding external service overhead.
# 
# Production Architecture Note:
# For a production application at scale, I would decouple background processing from 
# the web server using an out-of-process task queue (e.g., Redis + Celery / RQ) 
# to ensure persistent message queuing, worker isolation, and independent horizontal scaling.
executor = ThreadPoolExecutor(
    max_workers=4
)
