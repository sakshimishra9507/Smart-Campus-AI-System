import os
from django.db import connection
from django.http import JsonResponse
import redis
def healthz(request): return JsonResponse({"status":"ok"})
def readyz(request):
    checks={}
    try:
        with connection.cursor() as c: c.execute("SELECT 1")
        checks["database"]="ok"
    except Exception: checks["database"]="error"
    try:
        redis.Redis.from_url(os.environ["REDIS_URL"],socket_connect_timeout=1,socket_timeout=1).ping()
        checks["redis"]="ok"
    except Exception: checks["redis"]="error"
    ok=all(v=="ok" for v in checks.values())
    return JsonResponse({"status":"ok" if ok else "unready","checks":checks},status=200 if ok else 503)
