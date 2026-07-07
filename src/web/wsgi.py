"""Entry point WSGI para gunicorn/waitress: gunicorn 'src.web.wsgi:app' --bind 0.0.0.0:8000

Para desenvolvimento local: python -m src.web.wsgi
"""

from src.config import FLASK_HOST, FLASK_PORT
from src.web.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT)
