release: python manage.py migrate
web: gunicorn config.wsgi:application
worker: REMAP_SIGTERM=SIGQUIT celery worker --app=sodp --concurrency=1
beat: REMAP_SIGTERM=SIGQUIT celery beat --app=sodp --loglevel=info