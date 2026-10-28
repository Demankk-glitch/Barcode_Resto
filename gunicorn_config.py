import os

# Binding host dan port (mendukung dynamic PORT pada platform PaaS seperti Render / Heroku)
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Jumlah worker proses & thread
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("PYTHON_MAX_THREADS", "4"))
worker_class = "gthread"

# Timeout dan keep-alive
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
keepalive = 5

# Logging ke stdout / stderr agar terbaca di logs container / platform cloud
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("LOG_LEVEL", "info")
