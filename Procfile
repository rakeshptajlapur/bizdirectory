web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --log-file -
worker: celery -A config worker --loglevel=info
beat: celery -A config beat --loglevel=info