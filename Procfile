release: python manage.py migrate
web: gunicorn config.wsgi:application
worker: REMAP_SIGTERM=SIGQUIT celery worker --app=sodp --loglevel=info
beat: REMAP_SIGTERM=SIGQUIT celery beat --app=sodp --loglevel=info