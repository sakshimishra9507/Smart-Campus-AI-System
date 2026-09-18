# Deployment Guide

## Before Deployment

- Set `DEBUG=False`
- Use a strong `SECRET_KEY`
- Configure production database credentials
- Configure allowed hosts
- Configure HTTPS
- Configure static/media storage
- Run migrations
- Collect static files
- Create an admin account securely
- Review permissions

## Production Commands

```bash
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic
```

Do not use Django's development server as the production web server. Use a suitable WSGI/ASGI deployment setup.
