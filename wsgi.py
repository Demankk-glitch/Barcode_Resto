"""
WSGI Entrypoint untuk deployment production menggunakan Gunicorn / uWSGI.
Contoh eksekusi:
    gunicorn wsgi:app --config gunicorn_config.py
"""
from app import app

if __name__ == "__main__":
    app.run()
